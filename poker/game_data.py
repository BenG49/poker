'''Utility classes and enums for Game'''

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import List, Optional, Set, Tuple

from poker.util import same


class InvalidMoveError(ValueError):
    '''Invalid move supplied to game (e.g. negative raise)'''


class Action(Enum):
    '''
    Actions that a player can take:
    CALL:   call current bet, or check if there has been no raise
    RAISE:  raise by amt MORE THAN current bet
    ALL_IN: post all of player's chips
    FOLD:   fold

    Precedence for identical moves:
    - CALL over ALL_IN
    - ALL_IN over RAISE
    '''
    CALL = auto()
    RAISE = auto()
    ALL_IN = auto()
    FOLD = auto()

    def to_str(self, amt: Optional[int]) -> str:
        '''Action as string, meant to be concatednated to player name'''
        match self:
            case Action.CALL:   return 'called'
            case Action.RAISE:  return f'raised ${amt}'
            case Action.ALL_IN: return 'went all in'
            case Action.FOLD:   return 'folded'

    def to_short_str(self, amt: Optional[int]) -> str:
        '''Short string form (used in CFR)'''
        if self == Action.RAISE:
            return 'r' + str(amt)

        return {
            Action.ALL_IN: 'a',
            Action.CALL: 'c',
            Action.FOLD: 'f'
        }[self]

class BettingStage(Enum):
    '''Betting stages'''
    PREFLOP = auto()
    FLOP = auto()
    TURN = auto()
    RIVER = auto()

class PlayerState(Enum):
    '''
    Stores player's state for the current betting stage

    TO_CALL: still has to call, check, or raise
    MOVED:   called, checked, or raised
    ALL_IN:  went all in
    FOLDED:  folded
    OUT:     either not in the current hand or out of chips
    '''
    TO_MOVE = auto()
    MOVED = auto()
    ALL_IN = auto()
    FOLDED = auto()
    OUT = auto()

    def active(self) -> bool:
        '''True if player will still make moves in future betting stages'''
        return self in (PlayerState.TO_MOVE, PlayerState.MOVED)

class GameState(Enum):
    '''Poker game state'''
    OVER = auto()
    RUNNING = auto()
    HAND_DONE = auto()

@dataclass
class GameConfig:
    '''Stores configuration for fixed or no-limit hold'em game'''

    @staticmethod
    def nl(bb: int, min_bet: int=None) -> 'GameConfig':
        '''Create no-limit game'''
        return GameConfig(bb // 2, bb, 0, 0, bb if min_bet is None else min_bet)

    @staticmethod
    def fl(bb: int) -> 'GameConfig':
        '''Create fixed-limit game'''
        return GameConfig(bb // 2, bb, bb, bb * 2)

    @staticmethod
    def get_ante_idx(antes: List[int]) -> Optional[int]:
        '''Converts from deal-ordered list of antes to index of which player(s) recieve ante'''
        if same(antes):
            return None

        amt = max(antes)
        for i in (-1, 1, 0):
            if antes[i] == amt:
                # blinds are reversed for heads-up game
                if len(antes) == 2 and i >= 0:
                    return (i + 1) % 2
                return i

    # blinds
    small_blind: int
    big_blind: int

    # limits
    small_bet: int
    big_bet: int

    # minimum bet for the first raise of each round
    min_bet: int = 0

    # antes
    ante_amt: int = 0
    # None for antes for everyone, int selects player by deal order
    # e.g.: 0 small blind ante, 1 big blind ante, -1 button ante
    ante_idx: Optional[int] = None

    def has_blinds(self) -> bool:
        '''Game has blinds?'''
        return self.small_bet > 0 and self.big_bet > 0

    def is_limit(self) -> bool:
        '''Is game fixed-limit?'''
        return self.small_bet > 0 or self.big_bet > 0

@dataclass
class _PrevPot:
    '''Stores data for past pot, after pot has been split'''
    chips: int
    players_: set

    def players(self) -> Set[int]:
        '''Set of player ids in pot'''
        return self.players_

    def total(self) -> int:
        '''Total chips in pot'''
        return self.chips

    def fold(self, pl_id: int):
        '''Remove player from pot'''
        self.players_.remove(pl_id)

    def __repr__(self) -> str:
        return self.__str__()
    def __str__(self) -> str:
        p = ', '.join(f'P{p}' for p in self.players())
        return f'(${self.chips} {p})'

class Pots:
    '''Represent the current pot and all previous pots'''
    def __init__(self, players=None):
        if players is None:
            players = []

        self.raised = 0
        self.chips = 0
        self.bets = dict.fromkeys(players, 0)
        self.prev_pots: List[_PrevPot] = []

    def chips_to_call(self, pl_id: int) -> int:
        '''Minimum amount required to call for player'''
        return self.raised - self.bets.get(pl_id, 0)

    def players(self) -> Set[int]:
        '''Set of player ids in pot'''
        return self.bets.keys()

    def not_folded_players(self) -> Set[int]:
        '''Which players have not folded'''
        if len(self.prev_pots) > 0:
            return self.prev_pots[0].players()

        return self.players()

    def total(self) -> int:
        '''Total chips in pot and bets'''
        return self.chips + sum(self.bets.values())

    def total_all_pots(self) -> int:
        '''Total chips in ALL pots'''
        return self.total() + sum(pot.chips for pot in self.prev_pots)

    def bet(self, pl_id: int, chips: int):
        '''Add chips to pl_id's bet'''
        self.bets[pl_id] = chips + self.bets.get(pl_id, 0)
        self.raised = max(self.raised, self.bets[pl_id])

    def collect_bets(self):
        '''Put all bets in center'''
        self.raised = 0
        for p, bet in self.bets.items():
            self.chips += bet
            self.bets[p] = 0

    def fold(self, pl_id: int):
        '''Remove player from ALL pots, collect their bets'''
        self.chips += self.bets.get(pl_id, 0)
        self.bets.pop(pl_id)
        for pot in self.prev_pots:
            pot.fold(pl_id)

    def split(self):
        '''
        Splits pot into a number of side pots if this pot's bets
        are not equal, which assumes the player with the lowest
        bet is all-in.
        Should be called at the end of the hand.
        '''
        while not same(self.bets.values()):
            max_stake = min(self.bets.values())
            split = _PrevPot(0, set(self.players()))
            split.chips = max_stake * len(split.players()) + self.chips

            for p, bet in list(self.bets.items()):
                if bet == max_stake:
                    self.bets.pop(p)
                    continue

                self.bets[p] -= max_stake

            self.raised = max(self.bets.values())
            self.chips = 0
            self.prev_pots.append(split)

    def __iter__(self):
        '''Iterate over all pots'''
        yield from self.prev_pots
        yield self

    def __repr__(self) -> str:
        return self.__str__()
    def __str__(self) -> str:
        bets = ', '.join(f'P{p}:${b}' for p, b in sorted(self.bets.items()))
        out = f'(${self.chips}{" " if bets else ""}{bets})'
        return ', '.join([out, *(str(p) for p in reversed(self.prev_pots))])

@dataclass
class PlayerData:
    '''Public player data'''
    chips: int
    state: PlayerState

    def reset_state(self):
        '''Should be called at hand init, does not account for live bets'''
        if self.chips == 0:
            self.state = PlayerState.OUT
        else:
            self.state = PlayerState.TO_MOVE


Move = Tuple[Action, Optional[int]]

class Player(ABC):
    '''Abstract base class for players'''
    def __init__(self):
        self.hand = []
        self.id = None

    @abstractmethod
    def move(self, game) -> Move:
        '''Supply move given game state'''

    def chips(self, game) -> int:
        '''Helper method to get chips for current player'''
        return game.pl_data[self.id].chips

class EmptyPlayer(Player):
    '''Empty Player impl'''
    def move(self, _):
        ...
