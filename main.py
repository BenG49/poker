'''
main.py
'''
from itertools import combinations
import random

from agents import bots
from agents.boteval import boteval
from agents.cfr import CFR, CFRBot, InfoSet
from poker.game import Game

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

def main():
    BUY_IN = 1000
    BB = 20

    all_bots = [
        (lambda: bots.Raiser(BB), 'BB Raiser'),
        (bots.Folder,  'Folder'),
        (bots.Checker, 'Checker'),
        (bots.AllIn,   'All In'),
        (lambda: bots.Random(False), 'Random'),
    ]

    def g():
        return Game(BUY_IN, BB)

    for matchup in combinations(all_bots, 2):
        a, a_name = matchup[0]
        b, b_name = matchup[1]
        a_eval = boteval(a, b, g, 1000)

        if a_eval == 0:
            print(f'{a_name} ties {b_name}')
        else:
            winner, loser = (a_name, b_name) if a_eval > 0 else (b_name, a_name)

            print(f'{winner} beats {loser} by {abs(a_eval)} mbb/h')

if __name__ == '__main__':
    main()
