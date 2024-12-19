'''
Classes to simulate a Texas Holdem game.
'''
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, List, Dict, Tuple, Optional, Self

from poker import hands
from .hands import Hand
from .history import GameHistory
from .util import Action, BettingRound, Card, Deck, count, same

Move = Tuple[Action, Optional[int]]


class InvalidMoveError(ValueError): ...


class PlayerState(Enum):
    '''
    Stores player's state for the current betting round

    TO_CALL: still has to call, check, or raise
    MOVED:   called, checked, or raised
    ALL_IN:  went all in
    FOLDED:  folded
    OUT:     either not in the current hand or out of chips
    '''
    TO_CALL = 0
    MOVED = 1
    ALL_IN = 2
    FOLDED = 3
    OUT = 4

    def active(self) -> bool:
        '''True if player will still make moves in future betting rounds'''
        return self in (PlayerState.TO_CALL, PlayerState.MOVED)

class GameState(Enum):
    OVER = 0
    RUNNING = 1
    HAND_DONE = 2

# previous round pots should not have any bets, just chips
# to fold a player, their bet just goes into the pot and they are removed from every pot
@dataclass
class Pot:
    # chips in pot from previous betting rounds
    chips: int
    # bets in pot from current round { pl_id: chips }
    bets: Dict[int, int]

    ### MODIFIERS ###
    def fold(self, pl_id: int):
        '''Fold pl_id'''
        self.chips += self.bets.pop(pl_id, 0)

    def collect_bets(self):
        '''Put all bets in main pot'''
        for key, val in self.bets.items():
            self.chips += val
            self.bets[key] = 0

    def raised(self) -> int:
        '''The amount the pot has been raised'''
        return max([0, *self.bets.values()])

    ### GETTERS ###
    def total(self) -> int:
        '''Total chips in pot from all rounds'''
        return self.chips + sum(self.bets.values())

    def add(self, pl_id: int, chips: int):
        '''Add chips to pl_id's bet'''
        self.bets[pl_id] = chips + self.bets.get(pl_id, 0)

    def chips_to_call(self, pl_id: int) -> int:
        '''Minimum amount required to call'''
        return self.raised() - self.bets.get(pl_id, 0)

    def players(self) -> Iterator[int]:
        '''List of player ids in pot'''
        return self.bets.keys()

    def split(self) -> Optional[Self]:
        '''
        Splits pot into side pot if bets are not equal, which
        assumes that the player with the minimum bet is all-in.
        Should be called at the end of the hand.
        '''
        if same(self.bets.values()):
            return None

        max_stake = min(self.bets.values())
        next_bets = {}

        for pl_id, bet in self.bets.items():
            if bet == max_stake:
                continue

            self.bets[pl_id] = max_stake
            next_bets[pl_id] = bet - max_stake

        return Pot(0, next_bets)

    def __repr__(self) -> str:
        return self.__str__()
    def __str__(self) -> str:
        return f'(${self.chips} {", ".join(map(lambda x: f"PL{x[0]}:${x[1]}", self.bets.items()))})'

@dataclass
class PlayerData:
    '''Public player data'''
    chips: int
    latest_pot: int
    state: PlayerState

    def reset_state(self):
        '''Should be called at hand init, does not account for live bets'''
        if self.chips == 0:
            self.state = PlayerState.OUT
        else:
            self.state = PlayerState.TO_CALL

class Player(ABC):
    '''Abstract base class for players'''
    def __init__(self):
        self.hand = []
        self.id = None

    @abstractmethod
    def move(self, game) -> Move:
        ...

class Game:
    '''Game'''
    def __init__(self, buy_in: int, bigblind: int = 2):
        # constants
        self.buy_in: int = buy_in
        self.big_blind: int = bigblind
        self.small_blind: int = bigblind // 2

        self.state: GameState = GameState.HAND_DONE

        # game state
        self.button_id: int = 0
        self.sb_id: int = 0
        self.bb_id: int = 0

        self.current_pl_id: int = 0
        self.pl_data: List[PlayerData] = []
        self.community: List[Card] = []
        self.pots: List[Pot] = [Pot(0, {})]

        self.history: GameHistory = GameHistory()

        ### PRIVATE ###
        self._players: List[Player] = []
        self._deck: Deck = Deck()

    def __bet(self, pl_id: int, chips: int):
        if self.pl_data[pl_id].chips < chips:
            raise InvalidMoveError('Cannot put in more chips than available!')
        self.pl_data[pl_id].chips -= chips
        self.pots[self.pl_data[pl_id].latest_pot].add(pl_id, chips)

    def init_hand(self):
        '''Initializes a new hand'''
        for pl in self.pl_data:
            pl.reset_state()

        if count(self.in_hand_players()) < 2:
            self.state = GameState.OVER
            return
        self.state = GameState.RUNNING

        # add all players to pot in case game instantly ends
        for pl in self.in_hand_players():
            self.__bet(pl, 0)

        # blinds
        if len(self._players) == 2:
            self.sb_id = self.button_id
        else:
            self.sb_id = next(self.in_hand_players(start=self.button_id, skip_start=True))
        self.bb_id = next(self.in_hand_players(start=self.sb_id, skip_start=True))

        # small blind
        sb_amt = min(self.small_blind, self.pl_data[self.sb_id].chips)
        if sb_amt > 0:
            self.__bet(self.sb_id, sb_amt)
            self.history.add_action(
                BettingRound.PREFLOP,
                self.sb_id,
                (Action.ALL_IN, None) if sb_amt == self.pl_data[self.sb_id].chips
                    else (Action.RAISE, sb_amt)
            )

        # big blind
        bb_amt = min(self.big_blind, self.pl_data[self.bb_id].chips)
        if bb_amt > 0:
            self.__bet(self.bb_id, bb_amt)
            self.history.add_action(
                BettingRound.PREFLOP,
                self.bb_id,
                (Action.ALL_IN, None) if bb_amt == self.pl_data[self.bb_id].chips
                    else (Action.RAISE, bb_amt - sb_amt)
            )

        # deal hands
        self.community = []
        for pl in self._players:
            pl.hand = []
        self._deck.shuffle()
        for _ in range(2):
            for h in [(i + self.sb_id) % len(self._players) for i in range(len(self._players))]:
                self._players[h].hand.append(self._deck.deal())

        self.history.add_hands([pl.hand for pl in self._players])

        self.current_pl_id = next(self.in_hand_players(start=self.bb_id, skip_start=True))

    def step_move(self):
        '''Accept move from current player's entry in _players'''
        self.accept_move(*self._players[self.current_pl_id].move(self))

    def accept_move(self, action: Action, amt: int=None):
        '''Accept move, handle resulting game state'''
        if not self.running():
            return

        if self.current_pl_data.state.active():
            self.history.add_action(self.betting_round(), self.current_pl_id, (action, amt))
            bet = None

            if amt is not None and amt < 0:
                raise InvalidMoveError('Negative bet supplied!')

            if action == Action.FOLD:
                self.current_pl_pot.fold(self.current_pl_id)
                self.current_pl_data.state = PlayerState.FOLDED

            elif action == Action.CALL:
                bet = min(
                    self.chips_to_call(self.current_pl_id),
                    self.current_pl_data.chips
                )
                self.current_pl_data.state = PlayerState.MOVED

            elif action == Action.RAISE:
                bet = amt + self.chips_to_call(self.current_pl_id)
                self.current_pl_data.state = PlayerState.MOVED

            elif action == Action.ALL_IN:
                bet = self.current_pl_data.chips
                self.current_pl_data.state = PlayerState.ALL_IN

            if bet:
                if bet > self.chips_to_call(self.current_pl_id):
                    # make everyone else call this raise
                    for i, pl in enumerate(self.pl_data):
                        if i == self.current_pl_id:
                            continue
                        if pl.state == PlayerState.MOVED:
                            pl.state = PlayerState.TO_CALL
                self.__bet(self.current_pl_id, bet)

        self.current_pl_id = next(self.in_hand_players(skip_start=True))

        if (PlayerState.TO_CALL not in map(lambda p: p.state, self.pl_data)) or \
           self.not_folded_count() == 1:
            self.end_round()

    def end_round(self):
        '''Called at the end of a betting round'''
        # clear remaining bets into most up to date pot
        split = self.pots[-1].split()
        self.pots[-1].collect_bets()
        while split is not None:
            # move all players in last pot to new pot
            for pl in self.pots[-1].players():
                self.pl_data[pl].latest_pot += 1
            self.pots.append(split)

            split = self.pots[-1].split()
            self.pots[-1].collect_bets()

        # give everyone one turn
        for pl in self.pl_data:
            if pl.state == PlayerState.MOVED:
                pl.state = PlayerState.TO_CALL

        self.current_pl_id = next(self.in_hand_players(start=self.bb_id, skip_start=True))

        # check if only one player remaining or showdown
        if count(self.active_players()) < 2 or self.betting_round() == BettingRound.RIVER:
            self.end_hand()

        # deal next round
        if self.betting_round() != BettingRound.RIVER:
            self._deck.burn()
            if self.betting_round() == BettingRound.PREFLOP:
                self.community.extend(self.history.deal(self._deck.deal(3)))
            else:
                self.community.append(self.history.deal(self._deck.deal()))

    def end_hand(self):
        '''Called at the end of a hand (showdown or one player remaining)'''
        def pl_id(t: Tuple[int, Hand]):
            return t[0]
        def hand(t: Tuple[int, Hand]):
            return t[1]

        self.history.end_hand()

        # hand was ended before river, make the one person left win
        if self.not_folded_count() < 2:
            rankings = [
                (self._players[pl].id, -1 if self.pl_data[pl].state.active() else 0)
                for pl in range(len(self._players))
            ]
            rankings.sort(key=hand, reverse=True)
        else:
            # if hand was ended before river, deal rest of community
            while len(self.community) < 5:
                self._deck.burn()
                if self.betting_round() == BettingRound.PREFLOP:
                    self.community.extend(self.history.deal(self._deck.deal(3)))
                else:
                    self.community.append(self.history.deal(self._deck.deal()))

            rankings = sorted([
                (i, hands.evaluate([*self.community, *self._players[i].hand]))
                for i in self.pl_iter(exclude_states=(PlayerState.FOLDED,))
            ], key=lambda x: x[1], reverse=True)

        for pot_n, pot in enumerate(self.pots):
            pot_hands = list(filter(lambda x: pl_id(x) in pot.players(), rankings))
            winners = [pl_id(pl) for pl in pot_hands if hand(pl) == hand(pot_hands[-1])]
            win_value = pot.total() // len(winners)
            remainder = pot.total() % len(winners)
            self.history.add_result(pot_n, pot.total(), winners, rankings[-1][1])

            # give remainder to first player past button
            if remainder != 0:
                for i in self.pl_iter(start=self.button_id, skip_start=True):
                    if i in winners:
                        self.pl_data[i].chips += remainder
                        break

            # clear pots
            pot.chips = 0
            for pl in pot.players():
                pot.bets[pl] = 0

            # transfer to winners
            for winner in winners:
                self.pl_data[winner].chips += win_value

        self.button_id = next(self.in_hand_players(start=self.button_id, reverse=True, skip_start=True))
        self.state = GameState.HAND_DONE

    def step_hand(self):
        '''Run one hand'''
        self.init_hand()
        while self.running():
            self.step_move()

    ### GETTERS ###

    @property
    def current_pl_data(self) -> PlayerData:
        return self.pl_data[self.current_pl_id]

    @property
    def current_pl_pot(self) -> Pot:
        return self.pots[self.current_pl_data.latest_pot]

    def chips_to_call(self, pl_id: int) -> int:
        if self.pl_data[pl_id].state.active():
            return self.pots[self.pl_data[pl_id].latest_pot].chips_to_call(pl_id)
        return 0

    def running(self) -> bool:
        return self.state == GameState.RUNNING

    ### ITERATORS ###

    def pl_iter(
        self,
        start=None,
        reverse=False,
        include_states=tuple(PlayerState),
        exclude_states=(),
        skip_start=False
    ) -> Iterator[int]:
        '''
        Iterator over player ids

                 start: starting id, current_pl_id if None
               reverse: moves clockwise if true
        include_states: which states to include in iterator
        exclude_states: which states to exclude in iterator
            skip_start: skips start player
        '''
        start = self.current_pl_id if start is None else start
        reverse = -1 if reverse else 1
        first = skip_start

        for i in range(start, start + len(self._players) * reverse, reverse):
            idx = i % len(self._players)
            state = self.pl_data[idx].state
            if state in include_states and state not in exclude_states:
                if first:
                    first = False
                    continue
                yield idx

        # yield start player id at end
        if skip_start:
            yield start % len(self._players)

    def in_hand_players(self, start=None, reverse=False, skip_start=False) -> Iterator[int]:
        ''''Wrapper for pl_iter excluding players not in the current hand'''
        return self.pl_iter(start, reverse, exclude_states=(PlayerState.OUT,), skip_start=skip_start)

    def pldata_iter(
        self,
        start=None,
        reverse=False,
        include_states=tuple(PlayerState),
        exclude_states=(),
        skip_start=False
    ) -> Iterator[int]:
        '''pl_iter over pl_data'''
        return map(
            lambda i: self.pl_data[i],
            self.pl_iter(start, reverse, include_states, exclude_states, skip_start)
        )

    def not_folded_players(self, start=None, reverse=False, skip_start=False) -> Iterator[PlayerData]:
        '''Wrap pldata_iter for players that have not folded'''
        return self.pldata_iter(
            start, reverse,
            exclude_states=(PlayerState.OUT, PlayerState.FOLDED),
            skip_start=skip_start
        )

    def active_players(self, start=None, reverse=False, skip_start=False) -> Iterator[PlayerData]:
        '''Wrap pldata_iter for players that can make moves in the future'''
        return self.pldata_iter(
            start, reverse,
            include_states=(PlayerState.MOVED, PlayerState.TO_CALL),
            skip_start=skip_start
        )

    ### PLAYER COUNTS ###

    def not_folded_count(self) -> int:
        '''Counts # of players in game that haven't folded'''
        n = 0
        for pl in self.pl_data:
            if pl.state not in (PlayerState.FOLDED, PlayerState.OUT):
                n += 1
        return n

    ### MODIFIERS ###

    def add_player(self, player: Player):
        '''Add player to game'''
        player.id = len(self._players)
        self.pl_data.append(PlayerData(
            chips=self.buy_in,
            latest_pot=len(self.pots) - 1,
            state=PlayerState.TO_CALL)
        )
        self._players.append(player)

    ### NON-MODIFIER UTILS ###

    def betting_round(self) -> BettingRound:
        '''What the current betting round is'''
        return {
            0: BettingRound.PREFLOP,
            3: BettingRound.FLOP,
            4: BettingRound.TURN,
            5: BettingRound.RIVER
        }[len(self.community)]

    def raise_to(self, pl_id: int, raise_to: int) -> Optional[int]:
        '''Convert from raising to the overall pot raise TO raising from the current bet.'''
        current_raise = self.chips_to_call(pl_id)
        if current_raise > raise_to:
            return None
        return raise_to - current_raise

    def get_moves(self, pl_id: int) -> List[Move]:
        '''Return all possible moves for player pl_id.'''
        if not self.pl_data[pl_id].state.active() or not self.running():
            return []

        out = [(Action.FOLD, None)]

        free_chips = self.pl_data[pl_id].chips - self.chips_to_call(pl_id)
        if free_chips >= 0:
            out.append((Action.CALL, None))
            if free_chips > 0:
                out.append((Action.ALL_IN, None))
                out.extend([(Action.RAISE, i) for i in range(1, free_chips)])

        return out
