'''
main.py
'''
import functools
import random

from agents import bots
from agents import boteval
from agents.cfr import CFR, CFRBot, InfoSet
from poker.game import Game

CFR_GAME_CONFIG = {
    'buy_in': 2,
    'big_blind': 1
}

def train_cfr():
    cfr = CFR(players=2, game_settings=CFR_GAME_CONFIG)
    cfr.run(1)
    cfr.save_infosets('0.strat', 0)
    cfr.save_infosets('1.strat', 1)

def run_cfr_from_file():
    game = Game(**CFR_GAME_CONFIG)
    game.add_player(CFRBot(InfoSet.load_from_file('0.strat')))
    game.add_player(CFRBot(InfoSet.load_from_file('1.strat')))
    random.seed(0)
    game.step_hand()
    print(game.history)
    print(game.history.cards)

def main():
    boteval.run_tournament(
        {'buy_in': 1000, 'big_blind': 20},
        2_000,
        [
            (functools.partial(bots.HandValueBetter, n, p), f'Hand Value Better {n} {p}')
            for p in range(6, 18, 2)
            for n in range(20, 26, 2)
        ]
    )

if __name__ == '__main__':
    main()
