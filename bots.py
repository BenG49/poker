'''
Stores all poker bots
'''
from math import ceil
from game import Action, BettingRound, Game, Player
from util import Card, Hand, same

class Raiser(Player):
    def __init__(self, min_raise: int):
        super().__init__()
        self.min_raise = min_raise

    def move(self, game: Game):
        return Action.RAISE, self.min_raise

class Checker(Player):
    def move(self, game: Game):
        return Action.CALL, None

class Folder(Player):
    def move(self, game: Game):
        return Action.FOLD, None

class AllIn(Player):
    def move(self, game: Game):
        return Action.ALL_IN, None

class DumbBot(Player):
    def move(self, game: Game):
        if game.betting_round() == BettingRound.PREFLOP:
            self.starting_chips = game.current_pl_data.chips

        call_amt = game.current_pl_pot.chips_to_call(game.current_pl_id)

        # hand strength
        combined = sorted(self.hand + game.community, key=Card.get_rank)
        hand_type = Hand.PAIR if same(combined[:2]) or same(combined[-2:]) else Hand.HIGH
        if len(combined) >= 5:
            hand_type = Hand.get_highest_hand(*combined).hand_type

        BB = -1
        p={# [PREFLOP, FLOP, TURN, RIVER]
Hand.HIGH:      [2*BB, 2*BB, BB,   BB  ],
Hand.PAIR:      [0.03, 0.03, 0.03, 0.04],
Hand.TPAIR:     [0.00, 0.00, 0.30, 0.30],
Hand.TRIPS:     [0.00, 0.70, 0.70, 0.70],
Hand.STRAIGHT:  [0.00, 0.00, 0.00, 1.00],
Hand.FLUSH:     [0.00, 0.00, 0.00, 1.00],
Hand.FULL:      [0.00, 0.00, 0.00, 0.90],
Hand.FOURS:     [0.00, 1.00, 1.00, 1.00],
Hand.STR_FLUSH: [0.00, 0.00, 1.00, 1.00],
        }[hand_type][game.betting_round().value]

        put_in_pct = (self.starting_chips - game.current_pl_data.chips) / self.starting_chips
        amt = 0
        if p > put_in_pct:
            amt = ceil((p - put_in_pct) * self.starting_chips)

        bb_min = p / BB * game.big_blind

        if p < 0 and bb_min >= call_amt or amt == call_amt:
            return Action.CALL, None
        if amt == game.current_pl_data.chips:
            return Action.ALL_IN, None
        if amt > call_amt:
            return Action.RAISE, amt - call_amt
        return Action.FOLD, None
