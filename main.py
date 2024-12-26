'''
main.py
'''
import random

from agents import bots
from agents import boteval
from agents.cfr import CFR, CFRBot, InfoSet
from poker import phh
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
            [lambda: bots.Raiser(20),    'BB Raiser'],
            [bots.Folder,                'Folder'],
            [bots.Checker,               'Checker'],
            [bots.AllIn,                 'All In'],
            # [lambda: bots.Random(False), 'Random'],
            [bots.PocketPairSeeker,      'Pocket Pair Seeker'],
            [bots.HandValueBetter,       'Hand Value Better'],
        ]
    )

if __name__ == '__main__':
    game = Game(1000, 20)
    game.add_player(bots.HandValueBetter())
    game.add_player(bots.Checker())
    game.step_hand()
    game.step_hand()
    with open('out-1.phh', 'w', encoding='utf-8') as f:
        f.write(phh.dump(game.history, 0))
    with open('out-2.phh', 'w', encoding='utf-8') as f:
        f.write(phh.dump(game.history, 1))

    # might open empty file if game ends after one hand
    with open('out-2.phh', 'rb') as f:
        loaded = phh.load(f)
        print(loaded)
        print()
        for state in Game.replay(loaded):
            print(state)
