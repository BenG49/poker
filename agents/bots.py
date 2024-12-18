'''
Stores all poker bots
'''
import random
from typing import List
from poker.game import Action, BettingRound, Game, Move, Player
from poker.hand import HandType, eval_hand, hand_type
from poker.util import Card, Deck, Rank, same

class Raiser(Player):
    def __init__(self, min_raise: int):
        super().__init__()
        self.min_raise = min_raise

    def move(self, game: Game) -> Move:
        if game.current_pl_data.chips < game.chips_to_call(self.id):
            return Action.ALL_IN, None
        return Action.RAISE, min(self.min_raise, game.current_pl_data.chips - game.chips_to_call(self.id))

class Checker(Player):
    def move(self, game: Game) -> Move:
        return Action.CALL, None

class Folder(Player):
    def move(self, game: Game) -> Move:
        return Action.FOLD, None

class AllIn(Player):
    def move(self, game: Game) -> Move:
        return Action.ALL_IN, None

class Random(Player):
    def __init__(self, fold: bool):
        super().__init__()
        self.fold = fold

    def move(self, game: Game) -> Move:
        moves = game.get_moves(self.id)
        if not self.fold:
            moves = [(a, v) for a, v in moves if a != Action.FOLD]
        return random.choice(moves)

class TerminalPlayer(Player):
    def move(self, game: Game) -> Move:
        print('Your turn.')
        print('Chips:', ', '.join(list(map(lambda p: f'P{p}:(${game.pl_data[p].chips}, bet ${game.current_pl_pot.bets.get(p, 0)})', game.pl_iter(skip_start=True)))))
        print('Community:', game.community)
        print('Your hand:', self.hand)
        print(f'Chips to call: ${game.chips_to_call(self.id)}')

        action = input('Choose action from: call, all in, raise, or fold: ').lower()[0]
        while action not in 'carf':
            print('Invalid input!')
            action = input('Choose action from: call, all in, raise, or fold: ').lower()[0]

        action = {'c': Action.CALL, 'a': Action.ALL_IN, 'r': Action.RAISE, 'f': Action.FOLD}[action]
        if action != Action.RAISE:
            return action, None

        amt = input('Amount to raise: ').strip()
        while not amt.isdecimal() or int(amt) > game.pl_data[self.id].chips:
            print('Non-numeric or too high raise!')
        amt = input('Amount to raise: ').strip()

        return action, int(amt)

class EquityBot(Player):
    @staticmethod
    def equity(betting_round: BettingRound, hand: List[Card], community: List[Card]) -> float:
        if betting_round == BettingRound.PREFLOP:
            def value(r: Rank) -> int:
                return r + 3 if r == Rank.ACE else r + 2
            ranks = list(map(Card.get_rank, hand))
            eq = 2 * value(max(ranks)) + value(min(ranks)) + 20
            if same(ranks):
                eq += 44
            if same(map(Card.get_suit, hand)):
                eq += 2
            return eq / 100.0

        # brute force outs
        combined = hand + community
        current_best = eval_hand(combined)
        outs = set()

        for card in iter(Deck()):
            if card in combined:
                continue

            new_best = eval_hand([*combined, card])

            # set minimum hand to 'win' at three of a kind
            if hand_type(new_best) > hand_type(current_best) and \
               hand_type(new_best) >= HandType.TPAIR:
                outs.add(card)

        return 2 * len(outs) / 100.0

    def pot_odds(self, game: Game) -> float:
        self_pot = game.pots[game.pl_data[self.id].latest_pot]
        total = self_pot.total() + self_pot.chips_to_call(self.id)
        return self_pot.chips_to_call(self.id) / total

    def move(self, game: Game) -> Move:
        eq = EquityBot.equity(game.betting_round(), self.hand, game.community)
        po = self.pot_odds(game)

        if eq < po:
            return Action.FOLD, None

        return Action.CALL, None
