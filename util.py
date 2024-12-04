'''
Utility classes Suit, Rank, Card, Hand
'''
from dataclasses import dataclass
from enum import IntEnum, StrEnum
from typing import List, Iterable

def same(it: Iterable) -> bool:
    last = None
    for i in it:
        if last is not None and last != i:
            return False
        last = i
    return True

class Suit(StrEnum):
    SPADES = '♠'
    HEARTS = '♥'
    DIAMONDS = '♦'
    CLUBS = '♣'

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

@dataclass
class Card:
    rank: Rank
    suit: Suit

    @staticmethod
    def gen_deck():
        return [Card(Rank(r), Suit(s)) for s in '♠♥♦♣' for r in [Rank.ACE] + list(range(Rank.TWO, Rank.ACE))]

    @staticmethod
    def make(s: str):
        assert len(s) == 2
        return Card(Rank.from_str(s[0]), Suit(s[1]))

    def get_rank(self):
        return self.rank

    def get_suit(self):
        return self.suit

    def __repr__(self) -> str:
        return self.__str__()
    def __str__(self) -> str:
        return Rank(self.rank).to_str() + str(self.suit)

# only stores hand value and representation, not actual hand data!
class Hand:
    @staticmethod
    def get_highest_hand(*cards: List[Card]):
        assert len(cards) == 7

        hands = []
        for i in range(6):
            for j in range(i+1, 7):
                hands.append(Hand([cards[idx] for idx in range(7) if idx not in (i, j)]))
        return max(hands)

    HIGH = 0
    PAIR = 3
    TPAIR = 4
    TRIPS = 5
    STRAIGHT = 6
    FLUSH = 7
    FULL = PAIR + TRIPS
    FOURS = 9
    STR_FLUSH = STRAIGHT + FLUSH

    def __init__(self, cards: List[Card]):
        assert len(cards) == 5

        cards.sort(key=Card.get_rank)
        ranks = list(map(Card.get_rank, cards))

        primary_indicies = list(range(5))
        low_ace = False

        hand_type = Hand.FLUSH if same(map(Card.get_suit, cards)) else 0

        if ranks == [Rank.TWO, Rank.THR, Rank.FOUR, Rank.FIVE, Rank.ACE]:
            hand_type += Hand.STRAIGHT
            low_ace = True
        elif ranks == [i for i in range(cards[0].rank, cards[0].rank+5)]:
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
        self.value = (hand_type << 28) | (primary_rank << 14) | secondary_rank
        self.string = str(cards)

    def __gt__(self, other) -> bool:
        return self.value > other.value

    def __eq__(self, other) -> bool:
        return self.value == other.value

    def __repr__(self) -> str:
        return self.__str__()
    def __str__(self) -> str:
        return self.string + f',{self.value >> 28}:{(self.value >> 14)&0x3FFF}:{self.value&0x3FFF}'
