'''
Classes to simulate a Texas Holdem game.
'''
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Iterator, List, Dict, Tuple, Optional, Self

from util import Deck, same, Card, Hand

class InvalidMoveError(ValueError): ...


class PlayerState(Enum):
    '''
    Stores player's state for the current betting round

    TO_CALL: still has to call, check, or raise
    MOVED:   called, checked, or raised
    ALL_IN:  went all in
    FOLDED:  folded
    '''
    TO_CALL = 0
    MOVED = 1
    ALL_IN = 2
    FOLDED = 3

    def active(self) -> bool:
        '''True if player will still make moves in future betting rounds'''
        return self in (PlayerState.TO_CALL, PlayerState.MOVED)

class Action(Enum):
    '''Actions that a playaer can take'''
    CALL = 0
    RAISE = 1
    ALL_IN = 2
    FOLD = 3

class BettingRound(Enum):
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3

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
    pl_id: int
    latest_pot: int
    state: PlayerState

class Player(ABC):
    '''Abstract base class for players'''
    def __init__(self):
        self.hand = []

    @abstractmethod
    def move(self, game) -> Tuple[Action, Optional[int]]:
        ...

class Game:
    '''Game'''
    def __init__(self, buy_in: int, bigblind: int = 2):
        # game state
        self.buy_in: int = buy_in
        self.big_blind: int = bigblind
        self.small_blind: int = bigblind // 2

        # game state
        self.button_id: int = 0
        self.sb_id: int = 0
        self.bb_id: int = 0

        self.current_pl_id: int = 0
        self.pl_data: List[PlayerData] = []
        self.community: List[Card] = []
        self.pots: List[Pot] = [Pot(0, {})]

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
        assert len(self._players) > 1

        # blinds
        if len(self._players) == 2:
            self.sb_id = self.button_id
        else:
            self.sb_id = self.pl_left(self.button_id)
        self.bb_id = self.pl_left(self.sb_id)
        self.__bet(self.sb_id, self.small_blind)
        self.__bet(self.bb_id, self.big_blind)

        # deal hands
        self.community = []
        for pl in self._players:
            pl.hand = []
        self._deck.shuffle()
        for _ in range(2):
            for h in [(i + self.sb_id) % len(self._players) for i in range(len(self._players))]:
                self._players[h].hand.append(self._deck.deal())

        # give everyone one turn
        for pl in self.pl_data:
            pl.state = PlayerState.TO_CALL

        self.current_pl_id = self.pl_left(self.bb_id)

    def step_move(self):
        '''
        Accept move from one player, handle resulting game state

        Basically step state machine forward with player move from player as input
        '''
        if self.current_pl_data.state.active():
            action, amt = self._players[self.current_pl_id].move(self)
            bet = None

            if action == Action.FOLD:
                self.current_pl_pot.fold(self.current_pl_id)
                self.current_pl_data.state = PlayerState.FOLDED

            elif action == Action.CALL:
                bet = self.current_pl_pot.chips_to_call(self.current_pl_id)
                self.current_pl_data.state = PlayerState.MOVED

            elif action == Action.RAISE:
                bet = amt + self.current_pl_pot.chips_to_call(self.current_pl_id)
                self.current_pl_data.state = PlayerState.MOVED

            elif action == Action.ALL_IN:
                bet = self.current_pl_data.chips
                self.current_pl_data.state = PlayerState.ALL_IN

            if bet:
                if bet > self.current_pl_pot.chips_to_call(self.current_pl_id):
                    # make everyone else call this raise
                    for pl in self.active_players(start=self.current_pl_id)[1:]:
                        pl.state = PlayerState.TO_CALL
                self.__bet(self.current_pl_id, bet)

        self.current_pl_id = self.pl_left(self.current_pl_id)

        # have all players moved for this round?
        # is there only one person left who can win?
        if len(self.pl_iter(include_states=[PlayerState.TO_CALL])) == 0 or \
           len(self.pl_iter(exclude_states=[PlayerState.FOLDED])) == 1:
            self.end_round()

    def end_round(self):
        '''Called at the end of a betting round'''
        # clear remaining bets into most up to date pot
        split = self.pots[-1].split()
        self.pots[-1].collect_bets()
        if split is not None:
            # move all players in last pot to new pot
            for pl in self.pots[-1].players():
                self.pl_data[pl].latest_pot += 1
            self.pots.append(split)

        # give everyone one turn
        for pl in self.active_players():
            pl.state = PlayerState.TO_CALL

        self.current_pl_id = self.pl_left(self.bb_id)

        # check if only one player remaining or showdown
        if len(self.active_players()) == 1 or \
           self.betting_round() == BettingRound.RIVER:
            self.end_hand()

        # deal next round
        if self.betting_round() != BettingRound.RIVER:
            self._deck.burn()
            if self.betting_round() == BettingRound.PREFLOP:
                self.community.extend(self._deck.deal(3))
            else:
                self.community.append(self._deck.deal())

    def end_hand(self):
        '''Called at the end of a hand (showdown or one player remaining)'''
        def pl_id(t: Tuple[int, Hand]):
            return t[0]
        def hand(t: Tuple[int, Hand]):
            return t[1]

        # if hand was ended before river, deal rest of community
        while len(self.community) < 5:
            self._deck.burn()
            if self.betting_round() == BettingRound.PREFLOP:
                self.community.extend(self._deck.deal(3))
            else:
                self.community.append(self._deck.deal())

        rankings = self.__get_hand_rankings()
        for pot in self.pots:
            pot_hands = list(filter(lambda x: pl_id(x) in pot.players(), rankings))
            winners = [pl_id(pl) for pl in pot_hands if hand(pl) == hand(pot_hands[-1])]
            win_value = pot.total() // len(winners)
            remainder = pot.total() % len(winners)

            if remainder != 0:
                raise NotImplementedError

            # clear pots
            pot.chips = 0
            for pl in pot.players():
                pot.bets[pl] = 0

            # transfer to winners
            for winner in winners:
                self.pl_data[winner].chips += win_value

        self.button_id = self.pl_right(self.button_id)

    def step_hand(self):
        self.init_hand()
        starting_button = self.button_id
        while self.button_id == starting_button:
            self.step_move()

    ### GETTERS ###

    @property
    def current_pl_data(self) -> PlayerData:
        return self.pl_data[self.current_pl_id]

    @property
    def current_pl_pot(self) -> Pot:
        return self.pots[self.current_pl_data.latest_pot]

    ### ITERATORS ###

    def pl_iter(
            self,
            start=None,
            include_states=(PlayerState.TO_CALL, PlayerState.MOVED, PlayerState.ALL_IN, PlayerState.FOLDED),
            exclude_states=()) -> Iterator[PlayerData]:
        start = self.current_pl_id if start is None else start
        def in_iter(pl: PlayerData) -> bool:
            return pl.state in include_states and pl.state not in exclude_states
        return [
            self.pl_data[i % len(self.pl_data)] for i in
            range(start, start + len(self.pl_data))
            if in_iter(self.pl_data[i % len(self.pl_data)])
        ]

    def active_players(self, start=None) -> Iterator[Player]:
        return self.pl_iter(start=start, include_states=(PlayerState.TO_CALL, PlayerState.MOVED))

    ### MODIFIERS ###

    def add_player(self, player: Player):
        '''Add player to game'''
        self.pl_data.append(PlayerData(
            chips=self.buy_in,
            pl_id=len(self._players),
            latest_pot=len(self.pots) - 1,
            state=PlayerState.TO_CALL))
        self._players.append(player)

    ### NON-MODIFIER UTILS ###

    def __get_hand_rankings(self) -> List[Tuple[int, Hand]]:
        '''Returns tuple of (pl_id, highest_hand) sorted by strength of hand of all players'''
        return sorted([
            (i, Hand.get_highest_hand(*self.community, *self._players[i].hand))
            for i in range(len(self._players))
            if self.pl_data[i].state != PlayerState.FOLDED
        ], key=lambda x: x[1])

    def betting_round(self) -> BettingRound:
        '''What the current betting round is'''
        return {
            0: BettingRound.PREFLOP,
            3: BettingRound.FLOP,
            4: BettingRound.TURN,
            5: BettingRound.RIVER
        }[len(self.community)]

    def pl_left(self, pl_id: int, n: int = 1) -> int:
        '''Player id to left of pl_id by n spots'''
        return (pl_id + n) % len(self._players)

    def pl_right(self, pl_id: int, n: int = 1) -> int:
        '''Player id to right of pl_id by n spots'''
        return (pl_id - n) % len(self._players)
