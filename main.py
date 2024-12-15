'''
main.py
'''
from agents import bots
from poker.game import Game

def main():
    game = Game(buy_in=1000, bigblind=10)
    game.add_player(bots.Raiser(game.small_blind))
    game.add_player(bots.EquityBot())
    game.step_hand()
    game.step_hand()
    print(game._history)

if __name__ == '__main__':
    main()
