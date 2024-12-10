'''
Utility classes Suit, Rank, Card, Hand
'''
from enum import IntEnum
from itertools import combinations
from random import shuffle
from typing import Dict, List, Iterable, Self

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
    SPADES = 0
    HEARTS = 1
    DIAMONDS = 2
    CLUBS = 3

    @staticmethod
    def from_str(s: str):
        return 'shdc'.index(s)

    def to_str(self) -> str:
        return 'shdc'[self.value]

class Rank(IntEnum):
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
    def from_str(s: str):
        return '23456789TJQKA'.index(s)

    def to_str(self) -> str:
        return '23456789TJQKA'[self.value]

class Card(int):
    '''6 bits: 2 suit + 4 rank'''
    def __new__(cls, rank: int, suit: int):
        instance = super().__new__(cls, (suit << 4) | rank)
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
        return Rank(self.rank).to_str() + Suit(self.suit).to_str()

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
        return min(map(Hand, combinations(cards, 5)))

    HIGH = 0
    PAIR = 3
    TPAIR = 4
    TRIPS = 5
    STRAIGHT = 6
    FLUSH = 7
    FULL = PAIR + TRIPS
    FOURS = 9
    STR_FLUSH = STRAIGHT + FLUSH

    STR_FLUSH_COUNT = 10
    FOURS_COUNT = 156
    FULL_COUNT = 156
    FLUSH_COUNT = 1277
    STRAIGHT_COUNT = 10 # no flushes
    TRIPS_COUNT = 858
    TPAIR_COUNT = 858
    PAIR_COUNT = 2860
    HIGH_COUNT = 1277

    HAND_COUNT = 7462

    STR_FLUSH_START = 1
    FOURS_START = STR_FLUSH_START + STR_FLUSH_COUNT
    FULL_START = FOURS_START + FOURS_COUNT
    FLUSH_START = FULL_START + FULL_COUNT
    STRAIGHT_START = FLUSH_START + FLUSH_COUNT
    TRIPS_START = STRAIGHT_START + STRAIGHT_COUNT
    TPAIR_START = TRIPS_START + TRIPS_COUNT
    PAIR_START = TPAIR_START + TPAIR_COUNT
    HIGH_START = PAIR_START + PAIR_COUNT

    FLUSH_BIT = 0x100000

    @staticmethod
    def lookup_key(ranks: List[int], flush: bool) -> int:
        '''Create lookup table key from 5 ranks (sorted) and flush bit'''
        key = Hand.FLUSH_BIT if flush else 0
        for i, rank in enumerate(ranks):
            key |= (rank & 0xF) << (4 * (4-i))
        return key

    @staticmethod
    def generate_lookup() -> Dict[int, int]:
        '''
        21 bit int (1 bit flush + 5x4 bit rank value, ordered 2->A) -> [1,7462] hand value
        '''

        lookup = {}

        # straight flushes + straights
        for i, h in enumerate([
            0x89ABC, # TJQKA
            0x789AB, # 9TJQK
            0x6789A, # 89TJQ
            0x56789, # 789TJ
            0x45678, # 6789T
            0x34567, # 56789
            0x23456, # 45678
            0x12345, # 34567
            0x01234, # 23456
            0x0123C, # 2345A
        ]):
            lookup[h] = Hand.STRAIGHT_START + i
            lookup[h | Hand.FLUSH_BIT] = Hand.STR_FLUSH_START + i

        # just do some first and then ill see how to generalize

        # fours, full house
        # aaaa b
        # aaa bb
        n = Hand.FOURS_COUNT - 1
        for a in iter(Rank):
            for b in iter(Rank):
                if a == b:
                    continue
                if a > b:
                    fours = Hand.lookup_key([b, a, a, a, a], False)
                    full = Hand.lookup_key([b, b, a, a, a], False)
                else:
                    fours = Hand.lookup_key([a, a, a, a, b], False)
                    full = Hand.lookup_key([a, a, a, b, b], False)

                lookup[fours] = n + Hand.FOURS_START
                lookup[fours | Hand.FLUSH_BIT] = n + Hand.FOURS_START
                lookup[full] = n + Hand.FULL_START
                lookup[full | Hand.FLUSH_BIT] = n + Hand.FULL_START
                n -= 1

        # trips
        # aaa bc
        n = Hand.TRIPS_COUNT - 1
        for a in iter(Rank):
            for b in iter(Rank):
                if a == b:
                    continue
                for c in range(0, b):
                    if a == c:
                        continue

                    hand = Hand.lookup_key(sorted([a, a, a, b, c]), False)
                    lookup[hand] = n + Hand.TRIPS_START
                    lookup[hand | Hand.FLUSH_BIT] = n + Hand.TRIPS_START
                    n -= 1

        # two pair
        # aabb c
        n = Hand.TPAIR_COUNT - 1
        for a in iter(Rank):
            for b in range(0, a):
                for c in iter(Rank):
                    if c in (a, b):
                        continue

                    hand = Hand.lookup_key(sorted([a, a, b, b, c]), False)
                    lookup[hand] = n + Hand.TPAIR_START
                    lookup[hand | Hand.FLUSH_BIT] = n + Hand.TPAIR_START
                    n -= 1

        # pair
        # aa bcd
        n = Hand.PAIR_COUNT - 1
        for a in iter(Rank):
            for b in iter(Rank):
                if a == b:
                    continue
                for c in range(0, b):
                    if a == c:
                        continue
                    for d in range(0, c):
                        if a == d:
                            continue

                        hand = Hand.lookup_key(sorted([a, a, b, c, d]), False)
                        lookup[hand] = n + Hand.PAIR_START
                        lookup[hand | Hand.FLUSH_BIT] = n + Hand.PAIR_START
                        n -= 1


        # high, flush
        # abcde
        n = Hand.HIGH_COUNT - 1
        for a in iter(Rank):
            for b in range(0, a):
                for c in range(0, b):
                    for d in range(0, c):
                        for e in range(0, d):
                            if [0, d - e, c - e, b - e, a - e] == [0, 1, 2, 3, 4]:
                                continue
                            if [e, d, c, b, a] == [0, 1, 2, 3, Rank.ACE]:
                                continue

                            hand = Hand.lookup_key([e, d, c, b, a], False)
                            lookup[hand] = n + Hand.HIGH_START
                            lookup[hand | Hand.FLUSH_BIT] = n + Hand.FLUSH_START
                            n -= 1

        return lookup

    @staticmethod
    def lookup(cards: List[Card]) -> int:
        '''Access hand ranking lookup table.'''
        flush = same(map(Card.get_suit, cards))
        cards.sort(key=Card.get_rank)

        return Hand.LOOKUP.get(Hand.lookup_key(cards, flush))

    def __new__(cls, cards: List[Card]) -> int:
        assert len(cards) == 5

        cards = list(cards)
        value = Hand.lookup(cards)

        instance = super().__new__(cls, value)
        instance.cards = cards
        return instance

    def __str__(self) -> str:
        return super().__str__() + ':' + str(self.cards)

Hand.LOOKUP = Hand.generate_lookup()
