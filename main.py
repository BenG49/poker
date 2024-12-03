from bots import Checker
from game import Game
import util

def main():
	game = Game().add_player(Checker(), 200).add_player(Checker(), 200)
	game.step_hand()

if __name__ == '__main__':
	main()
