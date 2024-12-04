'''
main.py
'''
from bots import Checker
from game import Game

def main():
    game = Game(buy_in=200)
    game.add_player(Checker())
    game.add_player(Checker())
    game.step_hand()

if __name__ == '__main__':
    main()
