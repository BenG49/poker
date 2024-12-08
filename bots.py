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

class TerminalPlayer(Player):
    def move(self, game: Game):
        print('Your turn.')
        print('Chips:', ', '.join(list(map(lambda p: f'P{p}:(${game.pl_data[p].chips}, bet ${game.current_pl_pot.bets.get(p, 0)})', game.pl_iter(skip_start=True)))))
        print('Community:', game.community)
        print('Your hand:', self.hand)
        print(f'Chips to call: ${game.current_pl_pot.chips_to_call(self.id)}')

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

# equity: probabilty of best hand
