'''
Utility classes Suit, Rank, Card, Hand
'''
from collections import Counter
from enum import Enum, IntEnum
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
    '''Suit enum'''
    SPADES = 0
    HEARTS = 1
    DIAMONDS = 2
    CLUBS = 3

    @staticmethod
    def from_str(s: str):
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
    def from_str(s: str):
        '''Create Rank from string'''
        return Rank('23456789TJQKA'.index(s))

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

class Card(int):
    '''6 bits: 2 suit + 4 rank'''
    def __new__(cls, rank: int, suit: int):
        instance = super().__new__(cls, (suit << 4) | rank)
        instance.rank = rank
        instance.suit = suit
        return instance

    @staticmethod
    def new(s: str):
        '''Create card from string, ex. Kh (king of hearts)'''
        assert len(s) == 2
        return Card(Rank.from_str(s[0]), Suit.from_str(s[1]))

    def get_rank(self):
        '''Rank getter'''
        return self.rank

    def get_suit(self):
        '''Suit getter'''
        return self.suit

    def __repr__(self) -> str:
        return self.__str__()
    def __str__(self) -> str:
        return Rank(self.rank).to_str() + Suit(self.suit).to_str()

class Deck:
    '''52-card list with helper methods for dealing'''
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
        '''Shuffle internal card list'''
        shuffle(self.deck)

class HandType(Enum):
    HIGH = 0
    PAIR = 1
    TPAIR = 2
    TRIPS = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL = 6
    FOURS = 7
    STR_FLUSH = 8

    def to_str(self) -> str:
        return [
            'High Card',
            'Pair',
            'Two Pair',
            'Three of a Kind',
            'Straight',
            'Flush',
            'Full House',
            'Four of a Kind',
            'Straight Flush'
        ][self.value]

class Hand(int):
    '''5-card hand class, only stores hand value, not list of Cards'''
    @staticmethod
    def get_best_hand(*cards: List[Card]) -> Self:
        '''Finds highest hand from list of cards'''
        assert len(cards) >= 5
        return min(map(Hand, combinations(cards, 5)))

    HAND_COUNT = 7462

    STR_FLUSH_COUNT = 10
    FOURS_COUNT = 156
    FULL_COUNT = 156
    FLUSH_COUNT = 1277
    STRAIGHT_COUNT = 10 # no flushes
    TRIPS_COUNT = 858
    TPAIR_COUNT = 858
    PAIR_COUNT = 2860
    HIGH_COUNT = 1277

    STR_FLUSH_BEST = 1
    FOURS_BEST = STR_FLUSH_BEST + STR_FLUSH_COUNT
    FULL_BEST = FOURS_BEST + FOURS_COUNT
    FLUSH_BEST = FULL_BEST + FULL_COUNT
    STRAIGHT_BEST = FLUSH_BEST + FLUSH_COUNT
    TRIPS_BEST = STRAIGHT_BEST + STRAIGHT_COUNT
    TPAIR_BEST = TRIPS_BEST + TRIPS_COUNT
    PAIR_BEST = TPAIR_BEST + TPAIR_COUNT
    HIGH_BEST = PAIR_BEST + PAIR_COUNT

    STR_FLUSH_WORST = FOURS_BEST - 1
    FOURS_WORST = FULL_BEST - 1
    FULL_WORST = FLUSH_BEST - 1
    FLUSH_WORST = STRAIGHT_BEST - 1
    STRAIGHT_WORST = TRIPS_BEST - 1
    TRIPS_WORST = TPAIR_BEST - 1
    TPAIR_WORST = PAIR_BEST - 1
    PAIR_WORST = HIGH_BEST - 1
    HIGH_WORST = HAND_COUNT

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
            lookup[h] = Hand.STRAIGHT_BEST + i
            lookup[h | Hand.FLUSH_BIT] = Hand.STR_FLUSH_BEST + i

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

                lookup[fours] = n + Hand.FOURS_BEST
                lookup[full] = n + Hand.FULL_BEST
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
                    lookup[hand] = n + Hand.TRIPS_BEST
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
                    lookup[hand] = n + Hand.TPAIR_BEST
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
                        lookup[hand] = n + Hand.PAIR_BEST
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
                            lookup[hand] = n + Hand.HIGH_BEST
                            lookup[hand | Hand.FLUSH_BIT] = n + Hand.FLUSH_BEST
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

    def rank_percentage(self) -> float:
        '''What percent of random hands are worse than this hand'''
        return 1 - self / Hand.HAND_COUNT

    def get_type(self) -> HandType:
        for t, best in enumerate([
            Hand.HIGH_BEST,
            Hand.PAIR_BEST,
            Hand.TPAIR_BEST,
            Hand.TRIPS_BEST,
            Hand.STRAIGHT_BEST,
            Hand.FLUSH_BEST,
            Hand.FULL_BEST,
            Hand.FOURS_BEST,
            Hand.STR_FLUSH_BEST
        ]):
            if self >= best:
                return HandType(t)

    def prettyprint(self) -> str:
        '''Pretty print hand type'''
        if self == 1:
            return 'Royal Flush'

        t = self.get_type()
        tstr = t.to_str()
        ranks = list(map(Card.get_rank, self.cards))

        if t in (HandType.STRAIGHT, HandType.STR_FLUSH):
            low = min(ranks)
            high = max(ranks)
            if low == Rank.TWO and high == Rank.ACE:
                low = Rank.ACE
                high = Rank.FIVE

            return f'{low.prettyprint()} to {high.prettyprint()} {tstr}'

        if t in (HandType.HIGH, HandType.FLUSH):
            return f'{tstr} ({max(ranks).prettyprint()} High)'

        counts = Counter(map(Card.get_rank, self.cards))

        if t in (HandType.PAIR, HandType.TRIPS, HandType.FOURS):
            prim_count = {HandType.PAIR: 2, HandType.TRIPS: 3, HandType.FOURS: 4}[t]
            prim = [r for r, n in counts.items() if prim_count == 2][0]
            second = max(filter(lambda c: c != prim, ranks))
            return f'{prim.prettyprint()} {tstr} ({second.prettyprint()} High)'

        if t == HandType.TPAIR:
            pairs_rank = [r for r, n in counts.items() if n == 2]
            return f'{pairs_rank[1].prettyprint()}, {pairs_rank[0].prettyprint()} {tstr}'
        if t == HandType.FULL:
            trip_rank = [r for r, n in counts.items() if n == 3][0]
            pair_rank = [r for r, n in counts.items() if n == 2][0]
            return f'{trip_rank.prettyprint()}, {pair_rank.prettyprint()} {tstr}'

    def __str__(self) -> str:
        return super().__str__() + ':' + str(self.cards)

Hand.LOOKUP = Hand.generate_lookup()

if __name__ == '__main__':
    ...
    # for k, v in sorted(Hand.LOOKUP.items(), key=lambda kv: kv[1]):
    #     print(f'{k}:{v}')
