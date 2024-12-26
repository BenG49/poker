'''Bot evaluator'''

from itertools import combinations
from typing import Callable, List, Tuple

from poker.game import Game, Player
from poker.util import count

def boteval(
        a_supplier: Callable[[], Player],
        b_supplier: Callable[[], Player],
        game_supplier: Callable[[], Game],
        rounds: int
    ) -> float:
    '''
    Evalulates two bots, returns mbb/g for player a (-mbb/g for player b).
    Runs flipped copies of each deal iterations/2 times.
    '''

    payoff = 0
    for _ in range(rounds // 2):
        game = game_supplier()
        game.add_player(a_supplier())
        game.add_player(b_supplier())
        game.init_hand()
        state = game.history._hands[0], game._deck.deck
        while game.running():
            game.step_move()
        payoff += game.pl_data[0].chips - game.buy_in

        game = game_supplier()
        game.add_player(b_supplier())
        game.add_player(a_supplier())
        game.init_hand()

        # set hand + deck state
        game._players[0].hand, game._players[1].hand = state[0]
        game.history._hands[0] = state[0]
        game._deck.deck = state[1]

        while game.running():
            game.step_move()
        payoff += game.pl_data[1].chips - game.buy_in

    return payoff / rounds / (game.big_blind / 1000.)

def run_tournament(game_config: dict, rounds: int, bots: List[Tuple[Callable[[], Player], str]]):
    '''Run round robin tournament between bots, print ranked results'''
    wins = [0 for _ in bots]
    ties = [0 for _ in bots]
    losses = [0 for _ in bots]
    netmbb = [0 for _ in bots]

    loops = count(combinations(bots, 2))
    dots = 0
    print('Running', loops, 'matchups: ', end='')
    for n, matchup in enumerate(combinations(enumerate(bots), 2)):
        i, (a, _) = matchup[0]
        j, (b, _) = matchup[1]
        a_eval = boteval(a, b, lambda: Game(**game_config), rounds)

        if a_eval == 0:
            ties[i] += 1
            ties[j] += 1
        else:
            if a_eval > 0:
                wins[i] += 1
                losses[j] += 1
            else:
                wins[j] += 1
                losses[i] += 1

            netmbb[i] += a_eval
            netmbb[j] -= a_eval

        while dots * loops / 10 < n:
            print('.', end='', flush=True)
            dots += 1
    print('.' * (10 - dots) + '\n')

    max_lengths = max(len(b[1]) for b in bots)
    def fmt(name, record, net, best_wins):
        def apply(color, s, apply):
            return f'\033[1;{color}m{s}\033[0m' if apply else s

        return ' '.join((
            f'{name.ljust(max_lengths)}',
            apply(31, f'{record[0]}/{record[1]}/{record[2]}', best_wins),
            apply(36, f'{round(net, 3):+}',                   net == max(netmbb))
        ))

    print('RESULTS:'.center(max_lengths), 'W/L/T', 'Net mbb/h')
    print('\n'.join([
        fmt(name, (w, l, t), net, line == 0)
        for line, (w, t, l, net, (_, name)) in
        enumerate(sorted(
            zip(wins, ties, losses, netmbb, bots),
            # sort by wins, then less losses, then less ties, then net rating
            key=lambda x: (x[0], -x[1], -x[2], x[3]),
            reverse=True
        ))
    ]))
