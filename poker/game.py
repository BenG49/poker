'''
Classes to run a N player No-Limit Texas Hold'em game.
'''
from typing import Iterator, List, Optional

from . import hands
from .game_data import (
    Action, BettingStage, EmptyPlayer, GameConfig, GameState, InvalidMoveError, Move, Player,
    PlayerData, PlayerState, Pot
)
from .history import GameHistory
from .util import Card, Deck, check_throw, count

class Game:
    '''N player No-Limit Texas Hold'em'''

    @staticmethod
    def replay(history: GameHistory, hand: int=0) -> Iterator['Game']:
        # pylint: disable=protected-access
        '''Replays game history with an iterator through each game state'''
        # NOTE: does not yield state between last move and showdown

        game = Game(0, history.cfg)
        for _ in range(history.players):
            game.add_player()

        for h, actions in enumerate(history.actions_by_hand()):
            # init chips
            for i, c in enumerate(history.chips[hand]):
                game.pl_data[history.to_game_index(h, i)].chips = c

            game.init_hand()
            # init hands, poke history
            game.history._hands[hand] = history._hands[hand]
            for i, hand_ in enumerate(history._hands[hand]):
                game._players[history.to_game_index(h, i)].hand = hand_

            yield game

            for action in actions:
                len_before = len(game.community)

                game.accept_move(*action.move)

                if len_before != len(game.community):
                    for i in range(len_before, len(game.community)):
                        game.community[i] = history.cards[hand][i]

                yield game

    def __init__(self, buy_in, cfg: GameConfig):
        # constants
        self.buy_in: int = buy_in
        self.cfg = cfg

        # game state
        self.state: GameState = GameState.HAND_DONE

        self.sb_id: int = -1
        self.bb_id: int = -1
        self.button_id: int = 0
        self.current_pl_id: int = -1

        # remaining raises allowed for current betting stage if fixed limit
        self.raises_left: int = -1
        self.last_raise: int = cfg.min_bet

        self.pl_data: List[PlayerData] = []
        self.community: List[Card] = []
        self.pots: List[Pot] = [Pot(0, {}, 0)]

        self.history: GameHistory = GameHistory(self.cfg)

        ### PRIVATE ###
        self._players: List[Player] = []
        self._deck: Deck = Deck()

    def __bet(self, pl_id: int, chips: int):
        # bets over limit should be validated beforehand, makes blinds simpler
        chips = min(chips, self.pl_data[pl_id].chips)
        self.pl_data[pl_id].chips -= chips
        self.pots[self.pl_data[pl_id].latest_pot].add(pl_id, chips)

    def init_hand(self):
        '''Initializes a new hand'''
        if count(self.in_hand_players()) < 2:
            self.state = GameState.OVER
            return
        self.state = GameState.RUNNING

        for pl in self.pl_data:
            pl.reset_state()

        # add all players to pot in case game instantly ends
        self.pots = [Pot(0, {p: 0 for p in self.in_hand_players()}, 0)]

        # deal hands
        self.community = []
        self._deck.shuffle()
        for p in self._players:
            p.hand = tuple(self._deck.deal(2))

        self.history.init_hand(
            self.chips(),
            [pl.hand for pl in self._players]
        )

        # blinds
        if count(self.in_hand_players()) == 2:
            self.sb_id = self.button_id
        else:
            self.sb_id = self.next_player(self.button_id)
        self.bb_id = self.next_player(self.sb_id)

        # small blind
        self.__bet(self.sb_id, self.cfg.small_blind)
        self.__bet(self.bb_id, self.cfg.big_blind)

        # antes
        if self.cfg.ante_amt > 0:
            match self.cfg.ante_idx:
                case None: ante_players = self.in_hand_players()
                case 1:    ante_players = (self.bb_id,)
                case -1:   ante_players = (self.button_id,)
            for i in ante_players:
                # antes go into main pot chips, not bets
                chips = min(self.cfg.ante_amt, self.pl_data[i].chips)
                self.pl_data[i].chips -= chips
                self.pots[self.pl_data[i].latest_pot].chips += chips

        # no matter what, rest of players have to match big blind raise
        self.pots[-1].total_raised = self.cfg.big_blind

        # reset number of raises allowed this round
        self.raises_left = 5
        self.last_raise = self.cfg.min_bet

        self.current_pl_id = self.next_player(self.bb_id)

    def step_move(self):
        '''Accept move from current player's entry in _players'''
        self.accept_move(*self._players[self.current_pl_id].move(self))

    def accept_move(self, action: Action, amt: int=None):
        '''Accept move, handle resulting game state'''
        if self.current_pl_data.state.active():
            self.validate_move(self.current_pl_id, action, amt, throws=True)

            action, amt = self.translate_move(self.current_pl_id, action, amt)

            bet = None
            match action:
                case Action.FOLD:
                    for pot in self.pots:
                        pot.fold(self.current_pl_id)
                    self.current_pl_data.state = PlayerState.FOLDED
                case Action.CALL:
                    bet = min(
                        self.chips_to_call(self.current_pl_id),
                        self.current_pl_data.chips
                    )
                    self.current_pl_data.state = PlayerState.MOVED
                case Action.RAISE:
                    bet = amt + self.chips_to_call(self.current_pl_id)
                    self.current_pl_data.state = PlayerState.MOVED
                    self.raises_left -= 1
                case Action.ALL_IN:
                    bet = self.current_pl_data.chips
                    self.current_pl_data.state = PlayerState.ALL_IN
                    if bet < self.get_current_limit() / 2:
                        self.raises_left -= 1

            if bet is not None:
                # make everyone else call this raise
                if bet > self.chips_to_call(self.current_pl_id):
                    self.last_raise = bet - self.chips_to_call(self.current_pl_id)
                    for i, pl in enumerate(self.pl_data):
                        if i == self.current_pl_id:
                            continue
                        if pl.state == PlayerState.MOVED:
                            pl.state = PlayerState.TO_MOVE
                self.__bet(self.current_pl_id, bet)

            self.history.add_action(self.betting_stage(), self.current_pl_id, (action, amt))

        self.current_pl_id = self.next_player()

        player_states = map(lambda p: p.state, self.pl_data)
        if PlayerState.TO_MOVE not in player_states or self.not_folded_count() == 1:
            self.end_round()

    def end_round(self):
        '''Called at the end of a betting stage'''
        # split pot into side pots
        self.pots += self.pots[-1].split()
        # collect bets
        for pot in self.pots:
            pot.collect_bets()
        # update latest pot for all players in latest pot
        for pl in self.pots[-1].players():
            self.pl_data[pl].latest_pot = len(self.pots) - 1

        to_move_count = 0
        # give everyone one turn
        for pl in self.pl_data:
            if pl.state == PlayerState.MOVED:
                pl.state = PlayerState.TO_MOVE

            if pl.state == PlayerState.TO_MOVE:
                to_move_count += 1

        self.current_pl_id = self.next_player(self.bb_id)

        # reset number of raises allowed this round
        self.raises_left = 5
        self.last_raise = self.cfg.min_bet

        # check if only one player remaining or showdown
        if to_move_count < 2 or self.betting_stage() == BettingStage.RIVER:
            self.end_hand()

        # deal next round
        else:
            ncards = 3 if self.betting_stage() == BettingStage.PREFLOP else 1
            self.community += self.history.deal(self._deck.deal(ncards))

    def end_hand(self):
        '''Called at the end of a hand (showdown or one player remaining)'''
        self.history.end_hand()

        # hand was ended before river, make the one person left win
        if self.not_folded_count() < 2:
            winners = list(self.pots[0].players())
            total = sum(p.total() for p in self.pots)

            self.history.add_result(total, winners, None)

            self.pl_data[winners[0]].chips += total
        else:
            # if hand was ended before river, deal rest of community
            while len(self.community) < 5:
                ncards = 3 if self.betting_stage() == BettingStage.PREFLOP else 1
                self.community += self.history.deal(self._deck.deal(ncards))

            rankings = sorted([
                (i, hands.evaluate([*self.community, *self._players[i].hand]))
                for i in self.not_folded_players()
            ], key=lambda x: x[1])

            for pot in self.pots:
                pot_rankings = [(p, r) for p, r in rankings if p in pot.players()]
                winners = [p for p, r in pot_rankings if r == pot_rankings[0][1]]
                win_value = pot.total() // len(winners)
                remainder = pot.total() % len(winners)

                self.history.add_result(pot.total(), winners, pot_rankings[0][1])

                # transfer to winners
                for winner in winners:
                    self.pl_data[winner].chips += win_value

                # give remainder to first player past button
                if remainder > 0:
                    i = self.next_player(self.button_id)
                    while i not in winners:
                        i += 1
                    self.pl_data[i].chips += remainder

        # clear pots
        self.pots = [Pot(0, {}, 0)]
        self.button_id = self.next_player(self.button_id, reverse=True)
        self.state = GameState.HAND_DONE

    def step_hand(self):
        '''Run one hand'''
        self.init_hand()
        while self.running():
            self.step_move()

    ### GETTERS ###

    @property
    def current_pl_data(self) -> PlayerData:
        '''Getter for current player's data'''
        return self.pl_data[self.current_pl_id]

    @property
    def current_pl_pot(self) -> Pot:
        '''Getter for the pot the current player is in'''
        return self.pots[self.current_pl_data.latest_pot]

    def chips(self) -> List[int]:
        '''List of chips for players'''
        return [p.chips for p in self.pl_data]

    def chips_to_call(self, pl_id: int) -> int:
        '''Helper for chips to call for player'''
        if self.pl_data[pl_id].state.active():
            return self.pots[self.pl_data[pl_id].latest_pot].chips_to_call(pl_id)
        return 0

    def running(self) -> bool:
        '''Is game running?'''
        return self.state == GameState.RUNNING

    def betting_stage(self) -> BettingStage:
        '''What the current betting stage is'''
        return {
            0: BettingStage.PREFLOP,
            3: BettingStage.FLOP,
            4: BettingStage.TURN,
            5: BettingStage.RIVER
        }[len(self.community)]

    def get_current_limit(self) -> int:
        '''Get fixed limit for current betting round'''
        if self.betting_stage() in (BettingStage.PREFLOP, BettingStage.FLOP):
            return self.cfg.small_bet
        return self.cfg.big_bet

    def raise_to(self, pl_id: int, raise_to: int) -> Optional[int]:
        '''Convert from raising to the overall pot raise TO raising from the current bet.'''
        current_raise = self.chips_to_call(pl_id)
        if current_raise > raise_to or raise_to - current_raise < self.last_raise:
            return None
        return raise_to - current_raise

    def get_moves(self, pl_id: int) -> Iterator[Move]:
        '''Iterator over all possible moves for player pl_id.'''
        if not self.pl_data[pl_id].state.active() or not self.running():
            return

        yield Action.FOLD, None

        to_call = self.chips_to_call(pl_id)
        free_chips = self.pl_data[pl_id].chips - to_call
        if free_chips < 0:
            yield Action.ALL_IN, None
        elif free_chips == 0:
            yield Action.CALL, None
        else:
            yield Action.CALL, None

            if self.cfg.is_limit():
                raise_amt = self.get_current_limit()
                # raise to complete limit if current raise is small
                if to_call < self.get_current_limit() / 2:
                    raise_amt -= to_call

                # if raise allowed
                if len(self._players) == 2 or self.raises_left > 0:
                    if free_chips <= raise_amt:
                        yield Action.ALL_IN, None
                    else:
                        yield Action.RAISE, raise_amt

                # all-in that doesn't count as a raise
                elif free_chips < self.get_current_limit() / 2:
                    yield Action.ALL_IN, None
            else:
                # no-limit
                yield from ((Action.RAISE, i) for i in range(max(1, self.last_raise), free_chips))
                yield Action.ALL_IN, None

    def translate_move(self, pl_id: int, action: Action, amt: int) -> Move:
        '''Translate move into standard move format'''
        if action == Action.RAISE:
            # autofill raise amount for FL game
            if amt is None and self.cfg.is_limit():
                amt = self.get_current_limit()
                # complete the bet if current raise is small
                if self.chips_to_call(pl_id) < self.get_current_limit() / 2:
                    amt -= self.chips_to_call(pl_id)

            if amt + self.chips_to_call(pl_id) == self.pl_data[pl_id].chips:
                return Action.ALL_IN, amt
            if amt == 0:
                return Action.CALL, None

        if action == Action.ALL_IN:
            return Action.ALL_IN, self.pl_data[pl_id].chips

        return action, amt

    @check_throw(InvalidMoveError)
    def validate_move(self, pl_id: int, action: Action, amt: int=None, throws: bool=False) -> bool:
        # pylint: disable=unused-argument, too-many-return-statements
        '''Validate move, throw InvalidMoveError if throws is True and move is invalid'''
        action, amt = self.translate_move(pl_id, action, amt)
        if amt is not None and amt < 0:
            return False, f'P{pl_id}: Positive value is required for amt.'

        if self.pl_data[pl_id].state != PlayerState.TO_MOVE:
            return False, f'Player {pl_id} has state {self.pl_data[pl_id].state.name}, cannot move.'

        at_bet_limit = self.cfg.is_limit() and len(self._players) > 2 and self.raises_left <= 0
        if (action == Action.RAISE or
               (action == Action.ALL_IN and amt >= self.get_current_limit() / 2)) and \
           at_bet_limit:
            return False, f'P{pl_id}: Cannot raise more than 5 times per round.'

        chips = self.pl_data[pl_id].chips
        to_call = self.chips_to_call(pl_id)

        if action == Action.CALL and chips < to_call:
            return False, (f'P{pl_id}: Cannot call {to_call} chips, '
                           f'more than available {chips} chips')

        if action == Action.RAISE:
            if amt is None or amt < 0:
                return False, f'P{pl_id}: Expected positive value for move RAISE.'

            if chips < to_call + amt:
                return False, (f'P{pl_id}: Cannot push in {to_call + amt} chips, '
                               f'more than available {chips} chips')

            if amt < self.last_raise:
                return False, (f'P{pl_id}: Cannot raise by {amt} chips, '
                               f'less than {self.last_raise} min bet/raise')

        return True, ''


    def next_player(self, pl_id: int=None, reverse: bool=False) -> int:
        '''Next in hand player after pl_id'''
        if pl_id is None:
            pl_id = self.current_pl_id

        out = (pl_id + (-1 if reverse else 1)) % len(self._players)

        if self.pl_data[out].state == PlayerState.OUT:
            return self.next_player(out, reverse)
        return out

    ### ITERATORS ###

    def in_hand_players(self) -> Iterator[int]:
        ''''Iterator of player ids excluding players not in the current hand'''
        for i, pl in enumerate(self.pl_data):
            if pl.state != PlayerState.OUT:
                yield i

    def not_folded_players(self):
        '''Return dict_iter of players that have not folded'''
        return self.pots[0].players()

    ### PLAYER COUNTS ###

    def not_folded_count(self) -> int:
        '''Counts # of players in game that haven't folded'''
        return len(self.pots[0].players())

    ### MODIFIERS ###

    def add_player(self, player: Player=EmptyPlayer()):
        '''Add player to game'''
        player.id = len(self._players)
        self.pl_data.append(PlayerData(
            chips=self.buy_in,
            latest_pot=len(self.pots) - 1,
            state=PlayerState.TO_MOVE)
        )
        self._players.append(player)

    def __str__(self) -> str:
        return (
            f'(P{self.current_pl_id} to move, {self.community}, '
            f'{[p.hand for p in self._players]}, {self.pots}, '
            f'{self.chips()})'
        )
