'''
Implements a Monte Carlo Counterfactual Regret Minimization bot
'''
from copy import deepcopy
from json import loads
from random import choices
import random
from typing import Dict, List
from poker.game import Game, GameState, Move, Player, PlayerState
from poker.util import Action, BettingStage, count


ActionHistT = Move | int

Strategy = Dict[Move, float]
Regret = Dict[Move, float]


def make_infoset_key(hand, community, bet_history: str) -> str:
    '''Generate key for the info set at the current node in the game tree'''
    hand = ''.join(str(c) for c in hand)
    community = ''.join(str(c) for c in community)
    return f'{hand}:{community:<10}:{bet_history}'

class CFRBot(Player):
    '''Plays by sampling from a supplied strategy dictionary'''
    def __init__(self, infosets: Dict[str, 'InfoSet']):
        super().__init__()
        self.infosets = infosets

    def move(self, game: Game) -> Move:
        bet_history = ' '

        last_stage = BettingStage.PREFLOP
        for action in game.history.actions:
            if action is None:
                bet_history += ' '
                last_stage = BettingStage.PREFLOP
                continue
            if action.stage != last_stage:
                last_stage = action.stage
                bet_history += '/'

            bet_history += action.move[0].to_short_str(action.move[1])

        key = make_infoset_key(
            self.hand,
            game.community,
             # most recent round betting history
            '' if len(bet_history.strip()) == 0 else bet_history.split()[-1]
        )

        # prevent crashing, folds if no infoset found
        infoset = self.infosets.get(
            key,
            InfoSet(key, self.id, [(Action.FOLD, None)])
        )
        strat = infoset.strategy
        actions = {a: strat.get(a, 0) for a in game.get_moves(self.id)}

        print(self.id, 'chose from strategy', infoset)

        return choices(
            population=list(actions.keys()),
            weights=list(actions.values())
        )[0]

class EmptyPlayer(Player):
    '''Empty Player impl'''
    def move(self, game: Game) -> Move:
        ...

HAND_DEAL = -1
BOARD_DEAL = -2

class History:
    '''
    Stores history for CFR

    Different from GameHistory because this history includes dealing as a chance action.
    '''
    def __init__(self, players: int, game_settings: dict):
        self.bet_history: str = ''

        self.last_card_dealt_count = 0
        self.game = Game(**game_settings)
        # add players
        for _ in range(players):
            self.game.add_player(EmptyPlayer())

    def is_done(self) -> bool:
        '''Ends game after one round'''
        return self.game.state != GameState.RUNNING and len(self.game.history.results) > 0 or \
            count(self.game.pl_iter(exclude_states=(PlayerState.FOLDED,))) < 2
        # or all but one all in and none to call

    def payoff(self, player: int) -> int:
        '''Payoff of player'''
        return self.game.pl_data[player].chips - self.game.buy_in

    def current_player(self) -> int:
        '''Returns player id to move or other chance action if cards need to be dealt'''
        # hand is not initialized, deal hands
        if self.game.state == GameState.HAND_DONE:
            return HAND_DEAL
        # check if card was dealt in game._history
        if self.last_card_dealt_count != len(self.game.history.cards[-1]):
            return BOARD_DEAL

        return self.game.current_pl_id

    def to_deal_card(self) -> bool:
        '''If the next action is to deal a card'''
        return self.current_player() in (HAND_DEAL, BOARD_DEAL)

    def deal(self) -> ActionHistT:
        '''Deal hand or update current state to realize that more cards have been dealt'''
        if self.game.state == GameState.HAND_DONE:
            random.seed(0)
            self.game.init_hand()
            self.last_card_dealt_count = len(self.game.history.cards[-1])
            return HAND_DEAL
        else:
            self.bet_history += '/'
            self.last_card_dealt_count = len(self.game.history.cards[-1])
            return BOARD_DEAL

    ### INFO SETS ###
    def current_pl_info_set_key(self) -> str:
        '''Generate key for the info set at the current node in the game tree'''
        return make_infoset_key(self.game._players[self.game.current_pl_id].hand, self.game.community, self.bet_history)

    def current_pl_new_info_set(self) -> 'InfoSet':
        '''Return infoset for current history state'''
        return InfoSet(
            self.current_pl_info_set_key(),
            self.game.current_pl_id,
            self.game.get_moves(self.game.current_pl_id)
        )

    def append(self, action: ActionHistT) -> 'History':
        '''
        Bet history as string:
        '/'   - end of betting stage
        'rXX' - raise by XX
        'c'   - call/check
        'f'   - fold
        'a'   - all in
        '''
        if not isinstance(action, int):
            self.bet_history += action[0].to_short_str(action[1])
            self.game.accept_move(*action)

        return self

    def __add__(self, action: ActionHistT) -> 'History':
        '''Returns copy with action inserted'''
        return deepcopy(self).append(action)

    def __str__(self) -> str:
        return f'{self.game.history._hands[0]}:{self.game.history.cards}:{self.bet_history}'
    def __repr__(self) -> str:
        return self.__str__()

class InfoSet:
    '''Subset of history for player i'''

    @staticmethod
    def load_from_file(file: str) -> Dict[str, 'InfoSet']:
        '''Loads stored strategy dict into Dict of infoset keys: infosets'''
        with open(file, 'r', encoding='utf-8') as f:
            def decode_action(s: str) -> Move:
                if s[0] in 'acf':
                    return {
                        'a': (Action.ALL_IN, None),
                        'c': (Action.CALL, None),
                        'f': (Action.FOLD, None),
                    }[s[0]]
                return Action.RAISE, int(s[1:])

            player = int(next(f).strip()[1:])
            out = {}
            for line in f:
                key, strat = line.strip().split('=')
                strat = {decode_action(k): v for k, v in loads(strat).items()}

                infoset = InfoSet(key, player, list(strat.keys()))
                infoset.strategy = strat

                out[key] = infoset
            return out

    def __init__(self, key: str, player: int, _actions: List[Move]):
        self.key = key
        self.player = player
        self._actions = _actions
        self.regrets = {a: 0. for a in self.actions()}
        self.strategy_sum = {a: 0. for a in self.actions()}
        self.strategy = {}
        self.calculate_strategy()

    def actions(self) -> List[Move]:
        '''All actions that player i can take right now'''
        return self._actions

    def calculate_strategy(self):
        '''
        Calculate strategy from regrets.

        If no regrets have been collected, give each action an equal weighting.
        Otherwise, weight the action based on how large the regret for that action was.
        '''
        pos_regrets = {a: max(0, r) for a, r in self.regrets.items()}
        sum_regrets = sum(pos_regrets.values())

        if sum_regrets == 0:
            length = len(pos_regrets.keys())
            self.strategy = {a: 1 / length for a in pos_regrets.keys()}
        else:
            self.strategy = {a: r / sum_regrets for a, r in pos_regrets.items()}

    def get_avg_strategy(self) -> Strategy:
        '''
        Get average strategy for this player over all iterations.

        If no strategies have been run, give each action an equal weighting.
        '''
        cumulative_strat = {a: self.strategy_sum.get(a, 0) for a in self.actions()}
        # how many strategies have been averaged in
        strategy_sum = sum(cumulative_strat.values())

        if strategy_sum == 0:
            length = len(cumulative_strat.keys())
            return {a: 1 / length for a in cumulative_strat.keys()}
        else:
            return {a: s / strategy_sum for a, s in cumulative_strat.items()}

    def __str__(self) -> str:
        return '{' + ', '.join(
            '"' + a[0].to_short_str(a[1]) + '": ' + str(round(v, 3))
            for a, v in self.strategy.items()
        ) + '}'
    def __repr__(self) -> str:
        return self.__str__()

class CFR:
    def __init__(self, players: int, game_settings: dict):
        self.players = players
        self.info_sets: Dict[str, InfoSet] = {}
        self.game_settings = game_settings

    def _get_info_set(self, h: History) -> InfoSet:
        '''Get info set for next player to move from given history'''
        key = h.current_pl_info_set_key()
        if key not in self.info_sets:
            self.info_sets[key] = h.current_pl_new_info_set()
        return self.info_sets[key]

    def step_tree(self, h: History, player: int, p_i: float, p_minus_i: float) -> float:
        '''
        p_i: p(player reaching current state) (based on chance actions and number of choices)
        p_minus_i: p(reaching current state if player takes all actions required),
                   all outside probabilities

        Calculates regret for each other possible action
        Update strategy with regret matching

        Returns expected payoff for history h
        '''
        if h.is_done():
            return h.payoff(player)
        elif h.to_deal_card():
            deal_action = h.deal()
            return self.step_tree(h.append(deal_action), player, p_i, p_minus_i)

        info_set = self._get_info_set(h)
        payoff = 0
        payoffs: Dict[Move, float] = {}

        ### RECURSE THROUGH TREE AND CALCULATE PAYOFF ###
        for action in info_set.actions():
            if h.current_player() == player:
                # probability of taking this strategy affects probability for p_i
                payoffs[action] = self.step_tree(
                    h + action, player, p_i * info_set.strategy[action], p_minus_i)
            else:
                # probability of taking this strategy affects probability for p_minus_i
                payoffs[action] = self.step_tree(
                    h + action, player, p_i, p_minus_i * info_set.strategy[action])

            # weight payoff of each action by probability of taking this action
            payoff += payoffs[action] * info_set.strategy[action]

        ### UPDATE PLAYER ###
        if h.current_player() == player:
            for action in info_set.actions():
                # update cumulative strategy
                info_set.strategy_sum[action] += p_i * info_set.strategy[action]

                # update total regrets
                ### REGRET[ACTION] = p_minus_i * (PAYOFF OF TAKING ACTION - AVERAGE PAYOFF)
                info_set.regrets[action] += p_minus_i * (payoffs[action] - payoff)

            info_set.calculate_strategy()

        return payoff

    def save_infosets(self, file: str, player: int):
        '''Save infosets to file f'''
        with open(file, 'w', encoding='utf-8') as f:
            f.write(f'P{player}\n')
            for k, infoset in self.info_sets.items():
                if infoset.player == player:
                    f.write(k)
                    f.write('=')
                    f.write(str(infoset))
                    f.write('\n')


    # TODO: test subset:
    #       - limit card possibilities
    #       - limit possible bets
    def run(self, iterations: int):
        for t in range(iterations):
            for p in range(self.players):
                self.step_tree(History(self.players, self.game_settings), p, 1, 1)

            print('Completed iteration', t)
