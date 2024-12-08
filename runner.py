from game import Game, GameState

class BotTUI:
    def __init__(self, game: Game):
        self.game = game

    def dict_str(self, it):
        return ', '.join(map(lambda t: f'{t[0]}: {t[1]}', enumerate(it)))

    def hand_str(self):
        return self.dict_str(list(map(lambda p: str(p.hand), self.game._players)))

    def run_hand(self):
        self.game.init_hand()

        if self.game.state == GameState.RUNNING:
            print()
            print('Chips:', self.dict_str(map(lambda x: x.chips, self.game.pl_data)))
            print('New Hands:', self.hand_str())
            print('PREFLOP')

        while self.game.state == GameState.RUNNING:
            action, amt = self.game._players[self.game.current_pl_id].move(self.game)
            start_round = self.game.betting_round()

            print(f' Player {self.game.current_pl_id} {action.to_str(amt)}')

            self.game.step_move()

            if start_round != self.game.betting_round():
                print(str(self.game.community)[1:-1])
                print(self.game.betting_round().name)

    def run_forever(self):
        self.run_hand()
        while self.game.state != GameState.OVER:
            self.run_hand()
