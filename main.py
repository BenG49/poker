'''
main.py
'''
import bots
from game import Game
from runner import BotTUI

def main():
    winners = {}
    for _ in range(50):
        game = Game(buy_in=1000, bigblind=10)
        game.add_player(bots.Raiser(game.big_blind))
        game.add_player(bots.Checker())
        game.add_player(bots.Folder())
        game.add_player(bots.AllIn())

        tui = BotTUI(game)
        tui.run_forever()
        chips = list(map(lambda x: x.chips, game.pl_data))
        for i, c in enumerate(chips):
            if c != 0:
                winners[i] = winners.get(i, 0) + 1

    print(winners)

if __name__ == '__main__':
    main()
