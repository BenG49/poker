'''
Utility classes Suit, Rank, Card, Hand
'''
from enum import IntEnum
from itertools import combinations
from random import shuffle
from typing import List, Iterable, Self

def same(it: Iterable) -> bool:
    '''True if all items in iterable are equal'''
    last = None
    for i in it:
        if last is not None and last != i:
            return False
        last = i
    return True

def it_len(it: Iterable) -> int:
    '''Loops through it to find length'''
    return sum(1 for _ in it)

class Suit(IntEnum):
    SPADES = 0 << 4
    HEARTS = 1 << 4
    DIAMONDS = 2 << 4
    CLUBS = 3 << 4

    @staticmethod
    def from_str(s: str):
        return 'shdc'.index(s)

    def to_str(self) -> str:
        return 'shdc'[self.value]

class Rank(IntEnum):
    TWO = 2
    THR = 3
    FOUR = 4
    FIVE = 5
    SIX = 6
    SEVEN = 7
    EIGHT = 8
    NINE = 9
    TEN = 10
    JACK = 11
    QUEEN = 12
    KING = 13
    ACE = 14

    @staticmethod
    def from_str(s: str):
        return '  23456789TJQKA'.index(s)

    def to_str(self) -> str:
        return '  23456789TJQKA'[self.value]

class Card(int):
    '''6 bits: 2 suit + 4 rank'''
    def __new__(cls, rank: int, suit: int):
        instance = super().__new__(cls, suit | rank)
        instance.rank = rank
        instance.suit = suit
        return instance

    @staticmethod
    def make(s: str):
        assert len(s) == 2
        return Card(Rank.from_str(s[0]), Suit.from_str(s[1]))

    def get_rank(self):
        return self.rank

    def get_suit(self):
        return self.suit

    def __repr__(self) -> str:
        return self.__str__()
    def __str__(self) -> str:
        return Rank(self.rank).to_str() + str(self.suit)

class Deck:
    def __init__(self):
        ranks = [Rank.ACE] + list(range(Rank.TWO, Rank.ACE))
        self.deck = [Card(Rank(r), Suit(s)) for s in iter(Suit) for r in ranks]

    def deal(self, n: int=1):
        '''Deal n cards, put those cards at the back of the deck'''
        assert n >= 1

        out = self.deck[-n:]
        self.deck = out + self.deck[:-n]
        return out[0] if n == 1 else out

    def burn(self, n: int=1):
        '''Wrapper, deal cards nowhere, put them at the back'''
        self.deal(n)

    def shuffle(self):
        shuffle(self.deck)

class Hand(int):
    '''5-card hand class, only stores hand value, not list of Cards'''
    @staticmethod
    def get_highest_hand(*cards: List[Card]) -> Self:
        '''Finds highest hand from list of cards'''
        assert len(cards) >= 5
        return max(map(Hand, combinations(cards, 5)))

    HIGH = 0
    PAIR = 3
    TPAIR = 4
    TRIPS = 5
    STRAIGHT = 6
    FLUSH = 7
    FULL = PAIR + TRIPS
    FOURS = 9
    STR_FLUSH = STRAIGHT + FLUSH

    def __new__(cls, cards: List[Card]) -> int:
        assert len(cards) == 5

        cards = list(cards)
        cards.sort(key=Card.get_rank)
        ranks = list(map(Card.get_rank, cards))

        primary_indicies = list(range(5))
        low_ace = False

        hand_type = Hand.FLUSH if same(map(Card.get_suit, cards)) else 0

        # straight, straight flush
        if ranks == [Rank.TWO, Rank.THR, Rank.FOUR, Rank.FIVE, Rank.ACE]:
            hand_type += Hand.STRAIGHT
            low_ace = True
        elif ranks == list(range(cards[0].rank, cards[0].rank+5)):
            hand_type += Hand.STRAIGHT
        # fours
        elif same(ranks[1:]):
            hand_type += Hand.FOURS
            primary_indicies = primary_indicies[1:]
        elif same(ranks[:-1]):
            hand_type += Hand.FOURS
            primary_indicies = primary_indicies[:-1]
        # middle trips, not pair
        elif same(ranks[1:-1]):
            hand_type += Hand.TRIPS
            primary_indicies = primary_indicies[1:-1]
        # top trips
        elif same(ranks[2:]):
            hand_type += Hand.TRIPS
            primary_indicies = primary_indicies[2:]
            if same(ranks[:-3]):
                hand_type += Hand.PAIR
        # bottom trips
        elif same(ranks[:-2]):
            hand_type += Hand.TRIPS
            primary_indicies = primary_indicies[:-2]
            if same(ranks[3:]):
                hand_type += Hand.PAIR
        # two pair
        elif same(ranks[1:3]) and same(ranks[3:5]):
            hand_type += Hand.TPAIR
            primary_indicies = primary_indicies[1:]
        elif same(ranks[0:2]) and same(ranks[3:5]):
            hand_type += Hand.TPAIR
            primary_indicies = [0, 1, 3, 4]
        elif same(ranks[0:2]) and same(ranks[2:4]):
            hand_type += Hand.TPAIR
            primary_indicies = primary_indicies[:4]

        # based on Kevin Watkins's blog post
        # bit values, high to low:
        # AKQJT98765432A
        def create_rank_value(ranks: List[Rank]) -> int:
            out = 0
            for rank in ranks:
                out += 1 << (0 if rank == Rank.ACE and low_ace else rank - 1)
            return out

        primary_rank = create_rank_value([ranks[i] for i in primary_indicies])
        secondary_rank = create_rank_value([ranks[i] for i in range(5) if i not in primary_indicies])

        # hand type:       4 bits
        # primary rank:   14 bits
        # secondary rank: 14 bits
        value = (hand_type << 28) | (primary_rank << 14) | secondary_rank

        instance = super().__new__(cls, value)
        instance.hand_type = hand_type
        instance.cards = cards
        return instance

    def __repr__(self) -> str:
        return self.__str__()
    def __str__(self) -> str:
        return str(self.cards) + f',{self >> 28}:{(self >> 14)&0x3FFF}:{self&0x3FFF}'
