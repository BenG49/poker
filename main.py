'''
main.py
'''
import agents.bots as bots
from poker.game import Game
from poker.runner import BotTUI

def main():
    game = Game(buy_in=1000, bigblind=10)
    game.add_player(bots.Raiser(game.small_blind))
    game.add_player(bots.EquityBot())

    tui = BotTUI(game)
    tui.run_hand()
    chips = list(map(lambda x: x.chips, game.pl_data))
    print(chips)

if __name__ == '__main__':
    main()
