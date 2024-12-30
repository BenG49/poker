'''Utility classes and enums for Game'''

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum, auto
from typing import Dict, Iterator, List, Optional, Tuple

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
    def nl(bb: int, min_bet: int=0) -> 'GameConfig':
        '''Create no-limit game'''
        # TODO: make min_bet default to big blind -- will change all test cases
        return GameConfig(bb // 2, bb, 0, 0, min_bet)

    @staticmethod
    def fl(bb: int) -> 'GameConfig':
        '''Create fixed-limit game'''
        return GameConfig(bb // 2, bb, bb, bb * 2)

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
    # None for antes for everyone, 1 for big blind ante, -1 for button ante
    ante_idx: Optional[int] = None

    def has_blinds(self) -> bool:
        '''Game has blinds?'''
        return self.small_bet > 0 and self.big_bet > 0

    def is_limit(self) -> bool:
        '''Is game fixed-limit?'''
        return self.small_bet > 0 or self.big_bet > 0

@dataclass
class Pot:
    '''Represent the pot or a side pot'''

    # chips in pot from previous betting stages
    chips: int
    # bets in pot from current round { pl_id: chips }
    bets: Dict[int, int]
    # amount raised (usually max bet)
    total_raised: int

    ### MODIFIERS ###
    def fold(self, pl_id: int):
        '''Fold pl_id'''
        self.chips += self.bets.pop(pl_id, 0)

    def collect_bets(self):
        '''Put all bets in main pot'''
        self.total_raised = 0
        for key, val in self.bets.items():
            self.chips += val
            self.bets[key] = 0

    def raised(self) -> int:
        '''The amount the pot has been raised'''
        return self.total_raised

    ### GETTERS ###
    def total(self) -> int:
        '''Total chips in pot from all hands'''
        return self.chips + sum(self.bets.values())

    def add(self, pl_id: int, chips: int):
        '''Add chips to pl_id's bet'''
        self.bets[pl_id] = chips + self.bets.get(pl_id, 0)
        self.total_raised = max(self.total_raised, self.bets[pl_id])

    def chips_to_call(self, pl_id: int) -> int:
        '''Minimum amount required to call'''
        return self.raised() - self.bets.get(pl_id, 0)

    def players(self) -> Iterator[int]:
        '''List of player ids in pot'''
        return self.bets.keys()

    def split(self) -> List['Pot']:
        '''
        Splits pot into a number of side pots (including 0) if
        this pot's bets are not equal, which assumes the player
        with the lowest bet is all-in.
        Should be called at the end of the hand.
        '''
        out = [self]

        while not same(out[-1].bets.values()):
            max_stake = min(out[-1].bets.values())
            next_bets = {}

            for pl_id, bet in out[-1].bets.items():
                if bet == max_stake:
                    continue

                out[-1].bets[pl_id] = max_stake
                next_bets[pl_id] = bet - max_stake

            out.append(Pot(0, next_bets, max(0, *next_bets.values())))

        # exclude 'self' from list
        return out[1:]

    def __repr__(self) -> str:
        return self.__str__()
    def __str__(self) -> str:
        bets = ', '.join(f'P{p}:${b}' for p, b in sorted(self.bets.items()))
        return f'(${self.chips}{" " if bets else ""}{bets})'

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
            self.state = PlayerState.TO_MOVE

        self.latest_pot = 0


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
