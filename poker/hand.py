'''
Functions to evaluate and rank poker hands
'''
from enum import IntEnum
from itertools import combinations
from typing import Dict, List, NewType

from poker.util import Card, Rank, same

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

Hand = NewType('Hand', int)

class HandType(IntEnum):
    '''Ranked categories of poker hands'''
    HIGH = 0
    PAIR = 1
    TPAIR = 2
    TRIPS = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL = 6
    FOURS = 7
    STR_FLUSH = 8
    ROYAL_FLUSH = 9

    def is_flush(self) -> bool:
        return self in (HandType.FLUSH, HandType.STR_FLUSH, HandType.ROYAL_FLUSH)

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
            'Straight Flush',
            'Royal Flush'
        ][self.value]

def eval_hand(cards: List[Card]) -> Hand:
    '''Finds highest hand from list of cards'''
    if len(cards) == 1:
        cards = cards[0]
    if len(cards) == 5:
        return lookup(list(cards))

    assert len(cards) > 5

    return min(map(eval_hand, combinations(cards, 5)))

def _lookup_key(ranks: List[int], flush: bool) -> int:
    '''Create lookup table key from 5 ranks (sorted) and flush bit'''
    key = FLUSH_BIT if flush else 0
    for i, rank in enumerate(ranks):
        key |= (int(rank) & 0xF) << (4 * (4-i))
    return key

def _generate_lookup() -> Dict[int, int]:
    '''
    21 bit int (1 bit flush + 5x4 bit rank value, ordered 2->A) -> [1,7462] hand value
    '''

    output = {}
    strings = [None] * (HAND_COUNT + 1)

    # straight flushes + straights
    for i, (h, s) in enumerate([
        (0x89ABC, 'Ten to Ace Straight'),
        (0x789AB, 'Nine to King Straight'),
        (0x6789A, 'Eight to Queen Straight'),
        (0x56789, 'Seven to Jack Straight'),
        (0x45678, 'Six to Ten Straight'),
        (0x34567, 'Five to Nine Straight'),
        (0x23456, 'Four to Eight Straight'),
        (0x12345, 'Three to Seven Straight'),
        (0x01234, 'Two to Six Straight'),
        (0x0123C, 'Ace to Five Straight'),
    ]):
        output[h] = STRAIGHT_BEST + i
        output[h | FLUSH_BIT] = STR_FLUSH_BEST + i

        strings[STRAIGHT_BEST + i] = s
        strings[STR_FLUSH_BEST + i] = s + ' Flush'
    strings[1] = 'Royal Flush'

    # fours, full house
    # aaaa b
    # aaa bb
    n = FOURS_COUNT - 1
    for a in iter(Rank):
        for b in iter(Rank):
            if a == b:
                continue
            if a > b:
                fours = _lookup_key([b, a, a, a, a], False)
                full = _lookup_key([b, b, a, a, a], False)
            else:
                fours = _lookup_key([a, a, a, a, b], False)
                full = _lookup_key([a, a, a, b, b], False)

            output[fours] = n + FOURS_BEST
            output[full] = n + FULL_BEST
            strings[n + FOURS_BEST] = f'{a.to_str()} Four of a Kind ({b.to_str()} High)'
            strings[n + FULL_BEST] = f'{a.to_str()}, {b.to_str()} Full House'

            n -= 1

    # trips
    # aaa bc
    n = TRIPS_COUNT - 1
    for a in iter(Rank):
        for b in iter(Rank):
            if a == b:
                continue
            for c in range(0, b):
                if a == c:
                    continue

                hand = _lookup_key(sorted([a, a, a, b, c]), False)
                output[hand] = n + TRIPS_BEST
                strings[n + TRIPS_BEST] = f'{a.to_str()} Three of a Kind ({b.to_str()} High)'
                n -= 1

    # two pair
    # aabb c
    n = TPAIR_COUNT - 1
    for a in iter(Rank):
        for b in range(0, a):
            for c in iter(Rank):
                if c in (a, b):
                    continue

                hand = _lookup_key(sorted([a, a, b, b, c]), False)
                output[hand] = n + TPAIR_BEST
                strings[n + TPAIR_BEST] = f'{a.to_str()}, {Rank(b).to_str()} Two Pair'
                n -= 1

    # pair
    # aa bcd
    n = PAIR_COUNT - 1
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

                    hand = _lookup_key(sorted([a, a, b, c, d]), False)
                    output[hand] = n + PAIR_BEST
                    strings[n + PAIR_BEST] = f'{a.to_str()} Pair ({b.to_str()} High)'
                    n -= 1


    # high, flush
    # abcde
    n = HIGH_COUNT - 1
    for a in iter(Rank):
        for b in range(0, a):
            for c in range(0, b):
                for d in range(0, c):
                    for e in range(0, d):
                        if [0, d - e, c - e, b - e, a - e] == [0, 1, 2, 3, 4]:
                            continue
                        if [e, d, c, b, a] == [0, 1, 2, 3, Rank.ACE]:
                            continue

                        hand = _lookup_key([e, d, c, b, a], False)
                        output[hand] = n + HIGH_BEST
                        output[hand | FLUSH_BIT] = n + FLUSH_BEST
                        strings[n + HIGH_BEST] = 'High Card (' + a.to_str() + ' High)'
                        strings[n + FLUSH_BEST] = 'Flush (' + a.to_str() + ' High)'
                        n -= 1

    return output, strings

def lookup(cards: List[Card]) -> int:
    '''Access hand ranking lookup table.'''
    flush = same(map(Card.get_suit, cards))
    cards.sort(key=Card.get_rank)

    return LOOKUP.get(_lookup_key(cards, flush))

def rank_percentage(hand: Hand) -> float:
    '''What percent of random hands are worse than this hand'''
    return 1 - hand / HAND_COUNT

def hand_type(hand: Hand) -> HandType:
    '''Retuns the HandType of a hand rank'''
    if hand == 1:
        return HandType.ROYAL_FLUSH

    for t, best in enumerate([
        HIGH_BEST,
        PAIR_BEST,
        TPAIR_BEST,
        TRIPS_BEST,
        STRAIGHT_BEST,
        FLUSH_BEST,
        FULL_BEST,
        FOURS_BEST,
        STR_FLUSH_BEST
    ]):
        if hand >= best:
            return HandType(t)

def prettyprint(hand: Hand) -> str:
    '''Pretty print hand type'''
    return STRINGS[hand]

# lookup table {hand: rank}, pretty printed strings ordered by rank
LOOKUP, STRINGS = _generate_lookup()
