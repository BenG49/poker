'''
main.py
'''
import random
from agents import bots
from agents.cfr import CFR, CFRBot, InfoSet
from poker.game import Game

def main():
    game = Game(buy_in=1000, bigblind=10)
    game.add_player(bots.Raiser(game.small_blind))
    game.add_player(bots.EquityBot())
    game.step_hand()
    game.step_hand()
    print(game.history)

GAME_CONFIG = {
    'buy_in': 2,
    'bigblind': 1
}

def train_cfr():
    cfr = CFR(players=2, game_settings=GAME_CONFIG)
    cfr.run(1)
    cfr.save_infosets('0.strat', 0)
    cfr.save_infosets('1.strat', 1)

def run_cfr_from_file():
    game = Game(**GAME_CONFIG)
    game.add_player(CFRBot(InfoSet.load_from_file('0.strat')))
    game.add_player(CFRBot(InfoSet.load_from_file('1.strat')))
    random.seed(0)
    game.step_hand()
    print(game.history)
    print(game.history.cards)

if __name__ == '__main__':
    main()
