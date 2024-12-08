'''
main.py
'''
import bots
from game import Game
from runner import BotTUI

def main():
    game = Game(buy_in=1000, bigblind=10)
    game.add_player(bots.Checker())
    game.add_player(bots.Checker())
    game.add_player(bots.Checker())
    game.add_player(bots.TerminalPlayer())

    tui = BotTUI(game)
    tui.run_hand()

    print()
    print(list(map(lambda x: x.chips, game.pl_data)))

if __name__ == '__main__':
    main()
