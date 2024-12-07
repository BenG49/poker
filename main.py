'''
main.py
'''
import bots
from game import Game, GameState

def main():
    game = Game(buy_in=1000, bigblind=10)
    game.add_player(bots.AllIn())
    game.add_player(bots.AllIn())
    game.add_player(bots.AllIn())
    game.add_player(bots.AllIn())

    for _ in range(50):
        game.init_hand()

        while game.state == GameState.RUNNING:
            game.step_move()
        if game.state == GameState.OVER:
            break

    print(list(map(lambda x: x.chips, game.pl_data)))

if __name__ == '__main__':
    main()
