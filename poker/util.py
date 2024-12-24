'''
Utility classes Suit, Rank, Card, Hand
'''
from copy import copy
from enum import Enum, IntEnum
from math import prod
from random import shuffle
from typing import Callable, List, Iterable, Optional

def same(it: Iterable) -> bool:
    '''True if all items in iterable are equal'''
    last = None
    for i in it:
        if last is not None and last != i:
            return False
        last = i
    return True

def count(it: Iterable) -> int:
    '''Loops through it to find length'''
    return sum(1 for _ in it)

def reorder(idx_to_idx: Callable[[int], int], l: List):
    '''Reorders list based on index mapping idx_to_idx'''
    out = [None] * len(l)
    for i, item in enumerate(l):
        out[idx_to_idx(i)] = item
    return out

class Action(Enum):
    '''
    Actions that a player can take:
    CALL:   call current bet, or check if there has been no raise
    RAISE:  raise by amt MORE THAN current bet
    ALL_IN: post all of player's chips
    FOLD:   fold
    '''
    CALL = 0
    RAISE = 1
    ALL_IN = 2
    FOLD = 3

    def to_str(self, amt: Optional[int]) -> str:
        if self == Action.CALL:
            return 'called'
        if self == Action.RAISE:
            return f'raised ${amt}'
        if self == Action.ALL_IN:
            return 'went all in'
        if self == Action.FOLD:
            return 'folded'

    def to_short_str(self, amt: Optional[int]) -> str:
        if self == Action.RAISE:
            return 'r' + str(amt)

        return {
            Action.ALL_IN: 'a',
            Action.CALL: 'c',
            Action.FOLD: 'f'
        }[self]

class BettingRound(Enum):
    PREFLOP = 0
    FLOP = 1
    TURN = 2
    RIVER = 3

class Suit(IntEnum):
    '''Suit enum'''
    SPADES = 0
    HEARTS = 1
    DIAMONDS = 2
    CLUBS = 3

    @staticmethod
    def from_str(s: str) -> 'Suit':
        '''Create Suit from string'''
        return Suit('shdc'.index(s))

    def to_str(self) -> str:
        '''Convert Suit to string'''
        return 'shdc'[self.value]

class Rank(IntEnum):
    '''Rank enum'''
    TWO = 0
    THR = 1
    FOUR = 2
    FIVE = 3
    SIX = 4
    SEVEN = 5
    EIGHT = 6
    NINE = 7
    TEN = 8
    JACK = 9
    QUEEN = 10
    KING = 11
    ACE = 12

    @staticmethod
    def from_str(s: str) -> 'Rank':
        '''Create Rank from string'''
        return Rank('23456789TJQKA'.index(s))

    def __init__(self, *args):
        super().__init__(args)
        # prime number associated with each rank
        self.prime = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37, 41][self.value]

    def to_str(self) -> str:
        ''' Convert Rank to string'''
        return '23456789TJQKA'[self.value]

    def prettyprint(self) -> str:
        return [
            'Two',
            'Three',
            'Four',
            'Five',
            'Six',
            'Seven',
            'Eight',
            'Nine',
            'Ten',
            'Jack',
            'Queen',
            'King',
            'Ace'
        ][self.value]

class Card:
    '''6 bits: 2 suit + 4 rank'''

    @staticmethod
    def new(s: str) -> 'Card':
        '''Create card from string, ex. Kh (king of hearts)'''
        assert len(s) == 2
        return Card(Rank.from_str(s[0]), Suit.from_str(s[1]))

    @staticmethod
    def from_int(i: int) -> 'Card':
        '''Create card from int representation'''
        assert (i & 0xF) < len(Rank)
        assert (i >> 4)  < len(Suit)
        return Card(i & 0xF, i >> 4)

    @staticmethod
    def prime_prod(cards: List['Card']) -> int:
        '''Return prime product of list of cards'''
        return prod(c.rank.prime for c in cards)

    def __init__(self, rank: int, suit: int):
        self.value = (suit << 4) | rank
        self.rank = rank
        self.suit = suit

        if not isinstance(self.rank, Rank):
            self.rank = Rank(self.rank)
        if not isinstance(self.suit, Suit):
            self.suit = Suit(self.suit)

    def get_rank(self) -> Rank:
        '''Rank getter'''
        return self.rank

    def get_suit(self) -> Suit:
        '''Suit getter'''
        return self.suit

    def __int__(self) -> int:
        return self.value

    def __eq__(self, other) -> bool:
        if isinstance(other, Card):
            return self.rank == other.rank and self.suit == other.suit
        return self.value & 0x3F == other & 0x3F

    def __hash__(self) -> int:
        return hash(self.value)

    def __repr__(self) -> str:
        return self.__str__()
    def __str__(self) -> str:
        return Rank(self.rank).to_str() + Suit(self.suit).to_str()

class Deck:
    '''52-card list with helper methods for dealing'''

    DECK = [Card(r, s) for s in iter(Suit) for r in [Rank.ACE] + list(range(Rank.TWO, Rank.ACE))]

    def __init__(self):
        self.deck = copy(Deck.DECK)

    def deal(self, n: int=1) -> List[Card]:
        '''Deal n cards, put those cards at the back of the deck'''
        assert n >= 1

        out = self.deck[-n:]
        self.deck = out + self.deck[:-n]
        return out

    def shuffle(self):
        '''Shuffle internal card list'''
        shuffle(self.deck)

    def __iter__(self):
        return iter(self.deck)
