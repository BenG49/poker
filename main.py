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
        [lambda: bots.Raiser(BB),    'BB Raiser'],
        [bots.Folder,                'Folder'],
        [bots.Checker,               'Checker'],
        [bots.AllIn,                 'All In'],
        [lambda: bots.Random(False), 'Random'],
        [bots.PocketPairSeeker,      'Pocket Pair Seeker'],
    ]

    # wins, ties, losses, net mbb/h
    results = [[0, 0, 0, 0] for _ in all_bots]

    def g():
        return Game(BUY_IN, BB)

    for matchup in combinations(enumerate(all_bots), 2):
        i, (a, _) = matchup[0]
        j, (b, _) = matchup[1]
        a_eval = boteval(a, b, g, 1000)

        if a_eval == 0:
            results[i][1] += 1
            results[j][1] += 1
        else:
            if a_eval > 0:
                results[i][0] += 1
                results[j][2] += 1
            else:
                results[j][0] += 1
                results[i][2] += 1

            results[i][3] += a_eval
            results[j][3] -= a_eval
        print('.', end='', flush=True)
    print('\n')

    max_lengths = max(len(b[1]) for b in all_bots)
    print('RESULTS:'.center(max_lengths), 'W/L/T', 'Net mbb/h')
    print('\n'.join([
        f'{name.ljust(max_lengths)} {w}/{l}/{t} {round(net, 3):+}'
        for (w, t, l, net), (_, name) in
        sorted(zip(results, all_bots), key=lambda x: x[0][0], reverse=True)
    ]))

if __name__ == '__main__':
    main()
