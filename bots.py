'''
Stores all poker bots
'''
from typing import Optional, Tuple
from game import Action, Game, Player

class Raiser(Player):
    def __init__(self, min_raise: int):
        super().__init__()
        self.min_raise = min_raise

    def move(self, game: Game) -> Tuple[Action, Optional[int]]:
        if game.current_pl_data.chips < game.current_pl_pot.chips_to_call(self.id):
            return Action.ALL_IN, None
        return Action.RAISE, min(self.min_raise, game.current_pl_data.chips - game.current_pl_pot.chips_to_call(self.id))

class Checker(Player):
    def move(self, game: Game) -> Tuple[Action, Optional[int]]:
        return Action.CALL, None

class Folder(Player):
    def move(self, game: Game) -> Tuple[Action, Optional[int]]:
        return Action.FOLD, None

class AllIn(Player):
    def move(self, game: Game) -> Tuple[Action, Optional[int]]:
        return Action.ALL_IN, None

class TerminalPlayer(Player):
    def move(self, game: Game) -> Tuple[Action, Optional[int]]:
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
