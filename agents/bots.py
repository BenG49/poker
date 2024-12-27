'''
Stores all poker bots
'''
import random
from typing import List
from poker import hands
from poker.game import Action, BettingStage, Game, Move, Player
from poker.hands import HandType
from poker.util import Card, Deck, Rank, same

class Raiser(Player):
    '''Raises by min_raise every turn'''
    def __init__(self, min_raise: int):
        super().__init__()
        self.min_raise = min_raise

    def move(self, game: Game) -> Move:
        if self.chips(game) - game.chips_to_call(self.id) <= self.min_raise:
            return Action.ALL_IN, None
        return Action.RAISE, self.min_raise

class Checker(Player):
    '''Checks/calls every turn'''
    def move(self, game: Game) -> Move:
        return Action.CALL, None

class Folder(Player):
    '''Folds every hand'''
    def move(self, game: Game) -> Move:
        return Action.FOLD, None

class AllIn(Player):
    '''Goes all in every hand'''
    def move(self, game: Game) -> Move:
        return Action.ALL_IN, None

class Random(Player):
    '''Randomly chooses from all moves, excluding folds if fold=False'''
    def __init__(self, fold: bool):
        super().__init__()
        self.fold = fold

    def move(self, game: Game) -> Move:
        moves = game.get_moves(self.id)
        if not self.fold:
            moves = [(a, v) for a, v in moves if a != Action.FOLD]
        return random.choice(moves)

class TerminalPlayer(Player):
    '''Terminal interface for human player'''
    def move(self, game: Game) -> Move:
        print('Your turn.')
        print('Chips:', ', '.join((
            f'P{p}:(${game.pl_data[p].chips}, bet ${game.current_pl_pot.bets.get(p, 0)})'
            for p in game.pl_iter()
        )))
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
    '''Stupid bot that tries to bet based on expected value'''
    @staticmethod
    def equity(stage: BettingStage, hand: List[Card], community: List[Card]) -> float:
        '''Calculate equity by brute forcing outs or calculating preflop hand value'''
        if stage == BettingStage.PREFLOP:
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
        current_best = hands.evaluate(combined)
        outs = set()

        for card in iter(Deck()):
            if card in combined:
                continue

            new_best = hands.evaluate([*combined, card])

            # set minimum hand to 'win' at three of a kind
            if hands.get_type(new_best) > hands.get_type(current_best) and \
               hands.get_type(new_best) >= HandType.TPAIR:
                outs.add(card)

        return 2 * len(outs) / 100.0

    def pot_odds(self, game: Game) -> float:
        '''Get current pot odds'''
        self_pot = game.pots[game.pl_data[self.id].latest_pot]
        total = self_pot.total() + self_pot.chips_to_call(self.id)
        return self_pot.chips_to_call(self.id) / total

    def move(self, game: Game) -> Move:
        eq = EquityBot.equity(game.betting_stage(), self.hand, game.community)
        po = self.pot_odds(game)

        if eq < po:
            return Action.FOLD, None

        return Action.CALL, None

class PocketPairSeeker(Player):
    '''All in on pocket pairs, fold otherwise'''
    def move(self, _: Game) -> Move:
        if same(map(Card.get_rank, self.hand)):
            return Action.ALL_IN, None
        return Action.FOLD, None

class HandValueBetter(Player):
    '''Bets based on value of hand, with cutoff values for folding'''
    def move(self, game: Game) -> Move:
        '''[1, 14]'''
        def card_value(card: Card):
            offset = 2 if card.rank == Rank.ACE else 1
            return card.rank + offset

        value = sum(card_value(card) for card in self.hand)
        pairs = same(map(Card.get_rank, self.hand))
        if pairs:
            value *= 2
        value_cutoff = 12 if pairs else 24
        if value < value_cutoff:
            return Action.FOLD, None

        pot_pct = value / (2 * card_value(Card(Rank.ACE, 0)))
        result = int(game.current_pl_pot.total() * pot_pct)
        raise_amt = game.raise_to(self.id, result)
        if raise_amt is None:
            return Action.FOLD, None

        if game.chips_to_call(self.id) > self.chips(game):
            return Action.FOLD, None
        return Action.RAISE, min(raise_amt, self.chips(game) - game.chips_to_call(self.id))
