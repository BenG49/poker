'''
Functions to evaluate and rank poker hands
'''
from enum import auto, Enum
from itertools import combinations
from typing import List

from .util import Card, Rank, same

class HandType(Enum):
    '''Ranked categories of poker hands'''
    HIGH = auto()
    PAIR = auto()
    TPAIR = auto()
    TRIPS = auto()
    STRAIGHT = auto()
    FLUSH = auto()
    FULL = auto()
    FOURS = auto()
    STR_FLUSH = auto()
    ROYAL_FLUSH = auto()

    def is_flush(self) -> bool:
        '''If hand type is a flush'''
        return self in (HandType.FLUSH, HandType.STR_FLUSH, HandType.ROYAL_FLUSH)

    def to_str(self) -> str:
        '''String hand description'''
        return [
            'High Card',
            'Pair',
            'Two Pair',
            'Three of a Kind',
            'Straight',
            'Flush',
            'Full House',
            'Four of a Kind',
            'Straight Flush',
            'Royal Flush'
        ][self.value]

class Hand(int):
    '''Prevent all these variables from polluting namespace'''
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
    def generate_lookup() -> tuple:
        '''
        Generates three lookup tables:
        2. (unique prime product of unsuited hand) -> hand rank
        1. (unique prime product of suited hand) -> hand rank
        3. hand rank -> hand string
        '''
        def key(*ranks) -> int:
            prod = 1
            for rank in ranks:
                prod *= Rank(rank).prime
            return prod

        unsuited = {}
        suited = {}
        strings = [None] * (Hand.HAND_COUNT + 1)

        # straight flushes + straights
        for i, (k, s) in enumerate([
            (31367009, 'Ten to Ace Straight'),
            (14535931, 'Nine to King Straight'),
            (6678671,  'Eight to Queen Straight'),
            (2800733,  'Seven to Jack Straight'),
            (1062347,  'Six to Ten Straight'),
            (323323,   'Five to Nine Straight'),
            (85085,    'Four to Eight Straight'),
            (15015,    'Three to Seven Straight'),
            (2310,     'Two to Six Straight'),
            (8610,     'Ace to Five Straight'),
        ]):
            unsuited[k] = Hand.STRAIGHT_BEST + i
            suited[k] = Hand.STR_FLUSH_BEST + i

            strings[Hand.STRAIGHT_BEST + i] = s
            strings[Hand.STR_FLUSH_BEST + i] = s + ' Flush'
        strings[1] = 'Royal Flush'

        # fours, full house
        n = Hand.FOURS_COUNT - 1
        for a in iter(Rank):
            for b in iter(Rank):
                if a == b:
                    continue

                unsuited[key(a, a, a, a, b)] = n + Hand.FOURS_BEST
                unsuited[key(a, a, a, b, b)] = n + Hand.FULL_BEST
                strings[n + Hand.FOURS_BEST] = f'{a.to_str()} Four of a Kind ({b.to_str()} High)'
                strings[n + Hand.FULL_BEST] = f'{a.to_str()}, {b.to_str()} Full House'

                n -= 1

        # trips
        n = Hand.TRIPS_COUNT - 1
        for a in iter(Rank):
            for b in iter(Rank):
                if a == b:
                    continue
                for c in range(0, b):
                    if a == c:
                        continue

                    unsuited[key(a, a, a, b, c)] = n + Hand.TRIPS_BEST
                    strings[n + Hand.TRIPS_BEST] = \
                        f'{a.to_str()} Three of a Kind ({b.to_str()} High)'
                    n -= 1

        # two pair
        n = Hand.TPAIR_COUNT - 1
        for a in iter(Rank):
            for b in range(0, a):
                for c in iter(Rank):
                    if c in (a, b):
                        continue

                    unsuited[key(a, a, b, b, c)] = n + Hand.TPAIR_BEST
                    strings[n + Hand.TPAIR_BEST] = f'{a.to_str()}, {Rank(b).to_str()} Two Pair'
                    n -= 1

        # pair
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

                        unsuited[key(a, a, b, c, d)] = n + Hand.PAIR_BEST
                        strings[n + Hand.PAIR_BEST] = f'{a.to_str()} Pair ({b.to_str()} High)'
                        n -= 1


        # high, flush
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

                            k = key(a, b, c, d, e)
                            unsuited[k] = n + Hand.HIGH_BEST
                            suited[k] = n + Hand.FLUSH_BEST
                            strings[n + Hand.HIGH_BEST] = 'High Card (' + a.to_str() + ' High)'
                            strings[n + Hand.FLUSH_BEST] = 'Flush (' + a.to_str() + ' High)'
                            n -= 1

        return unsuited, suited, strings

def evaluate(cards: List[Card]) -> int:
    '''Finds highest hand from list of cards'''
    if len(cards) == 1:
        cards = cards[0]
    if len(cards) == 5:
        return lookup(list(cards))

    assert len(cards) > 5

    return min(map(evaluate, combinations(cards, 5)))

def lookup(cards: List[Card]) -> int:
    '''Access hand ranking lookup table.'''
    lut = Hand.SUITED if same(map(Card.get_suit, cards)) else Hand.UNSUITED
    return lut.get(Card.prime_prod(cards))

def rank_pct(hand: Hand) -> float:
    '''What percent of random hands are worse than this hand'''
    return 1 - hand / Hand.HAND_COUNT

def get_type(hand: Hand) -> HandType:
    '''Retuns the HandType of a hand rank'''
    if hand == 1:
        return HandType.ROYAL_FLUSH

    for t, best in enumerate([
        Hand.PAIR_BEST,
        Hand.TPAIR_BEST,
        Hand.TRIPS_BEST,
        Hand.STRAIGHT_BEST,
        Hand.FLUSH_BEST,
        Hand.FULL_BEST,
        Hand.FOURS_BEST,
        Hand.STR_FLUSH_BEST
    ]):
        if hand >= best:
            return HandType(t)

    return Hand.HIGH_BEST

def to_str(hand: Hand) -> str:
    '''Pretty print hand type'''
    return Hand.STRINGS[hand]

# suited/unsuited lookup table {hand: rank}, pretty printed strings ordered by rank
Hand.UNSUITED, Hand.SUITED, Hand.STRINGS = Hand.generate_lookup()
