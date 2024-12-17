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

def train_cfr():
    cfr = CFR(players=2)
    cfr.run(1)
    cfr.save_infosets('a.strat')

def run_cfr_from_file():
    file = 'a.strat'
    infosets = InfoSet.load_from_file(file)

    game = Game(2, 0)
    game.add_player(CFRBot(infosets))
    game.add_player(CFRBot(infosets))
    random.seed(0)
    game.step_hand()
    print(game.history)
    print(game.history.cards)

if __name__ == '__main__':
    train_cfr()
    run_cfr_from_file()
