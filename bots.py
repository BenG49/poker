'''
Stores all poker bots
'''
from game import Action, Game, Player

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
