'''Bot evaluator'''

from typing import Callable

from poker.game import Game, Player

def set_cards_state(game, state):
    game._players[0].hand, game._players[1].hand = zip(state[0][::2], state[0][1::2])
    game.history._hands[0] = state[0]
    game._deck.deck = state[1]

def boteval(
        a_supplier: Callable[[], Player],
        b_supplier: Callable[[], Player],
        game_supplier: Callable[[], Game],
        rounds: int
    ) -> float:
    '''Evalulates two bots, returns mbb/g for player a (-mbb/g for player b)'''

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
        set_cards_state(game, state)
        while game.running():
            game.step_move()
        payoff += game.pl_data[1].chips - game.buy_in

    return payoff / rounds / (game.big_blind / 1000.)
