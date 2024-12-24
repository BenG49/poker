'''
Datastructure to store poker game history, works with Game from poker.game.
Stores and loads PHH file format.
'''
from typing import List, Optional, Tuple

from poker import hands
from poker.hands import Hand
from poker.util import Action, BettingRound, Card, reorder

Move = Tuple[Action, Optional[int]]

class GameHistory:
    '''Datastructure to store poker game history, works with Game from poker.game'''

    # round, player id, move
    # None is end of round specifier
    ActionTuple = Optional[Tuple[BettingRound, int, Move]]
    # pot total, winner list (first winner gets any remainder), best hand (-1 if win from fold), chips after round
    WinTuple = Tuple[int, List[int], Hand, List[int]]

    def __init__(self, players, buy_in, big_blind, small_blind):
        # assumes players all start with buy_in chips
        self.players = players
        self.buy_in = buy_in
        self.big_blind = big_blind
        self.small_blind = small_blind

        self.actions: List[GameHistory.ActionTuple] = []
        self.cards: List[List[Card]] = []
        self._hands: List[List[Tuple[Card]]] = []
        self.results: List[List[GameHistory.WinTuple]] = []

        self.hand_count = 0

    ### ADD TO HISTORY ###

    def add_hands(self, round_hands: List[List[Card]]):
        '''Add new round's hands to history'''
        self.hand_count += 1
        self.cards.append([])
        self._hands.append(reorder(
            lambda idx: self.to_history_index(self.hand_count - 1, idx),
            round_hands
        ))

    def add_action(self, bround: BettingRound, player: int, action: Move):
        '''Add player action to history'''
        self.actions.append((
            bround,
            self.to_history_index(self.hand_count - 1, player),
            action
        ))

    def deal(self, cards: List[Card]) -> List[Card]:
        '''Add dealt card to history'''
        self.cards[-1] += cards
        return cards

    def end_hand(self):
        '''Call before calling add_result, after the end of the hand, before processing pots'''
        self.results.append([])
        self.actions.append(None)

    def add_result(self, pot_amt: int, winners: List[int], top_hand: Hand, chips: List[int]):
        '''Add result for each pot processed'''
        self.results[-1].append((
            pot_amt,
            [self.to_history_index(self.hand_count - 1, w) for w in winners],
            top_hand,
            reorder(
                lambda idx: self.to_history_index(self.hand_count - 1, idx),
                chips
            )
        ))

    ### UTIL ###

    def to_history_index(self, hand: int, idx: int) -> int:
        '''Convert from game index (seats) to history index (dealing order)'''
        # start is always 1 for the first hand
        return (1 - hand + idx) % self.players

    def to_game_index(self, hand: int, idx: int) -> int:
        '''Convert from history index (dealing order) to game index (seats)'''
        # start is always 1 for the first hand
        return (idx - 1 + hand) % self.players

    def hand_actions(self, hand: int) -> List[ActionTuple]:
        '''Get actions taken in specific hand'''
        h = 0
        start = 0
        while h < hand:
            if self.actions[start] is None:
                h += 1
            start += 1
        end = start
        while True:
            if end == len(self.actions) or self.actions[end] is None:
                break
            end += 1
        return self.actions[start:end]

    def actions_by_round(self, hand: int) -> Tuple[list, list, list, list]:
        '''Split actions for hand into preflop, flop, turn, and river betting rounds'''
        lists = { r: [] for r in iter(BettingRound) }
        for action in self.hand_actions(hand):
            lists[action[0]].append(action)
        return (lists.get(r) for r in iter(BettingRound))

    ### FILE REPR ###

    def export(self, file: str, hand: int=0):
        '''TODO: add .phh extension, export to file-1, file-2 for hand 1, hand 2, if more than one hand'''

        def action_str(action) -> str:
            if action[2][0] == Action.FOLD:
                out = 'f'
            elif action[2][0] == Action.CALL:
                out = 'cc'
            else:
                out = f'cbr {action[2][1]}'
            out = f'"p{action[1]+1} {out}",'

            if action[2][0] == Action.ALL_IN:
                out += ' # All-in'
            return out

        # there are not enough hands to export requested hand
        if self.hand_count < hand + 1:
            open(file, 'w', encoding='utf-8').close()
            return

        chips = [self.buy_in] * self.players
        if hand > 0:
            chips = self.results[hand - 1][-1][3]
        with open(file, 'w', encoding="utf-8") as f:
            f.write('variant = "NT"\n')
            f.write(f'antes = {[0] * self.players}\n')
            blinds = [self.small_blind, self.big_blind] + [0] * (self.players - 2)
            f.write(f'blinds_or_straddles = {blinds}\n')
            f.write('min_bet = 0\n')
            f.write(f'starting_stacks = {chips}\n')
            f.write(f'seats = {self.players}\n')
            f.write(f'hand = {hand+1}\n')
            f.write('actions = [\n')

            board = self.cards[hand]
            preflop, flop, turn, river = self.actions_by_round(hand)
            # remove blind actions
            preflop = preflop[2:]

            # showing holecards
            folded = set(i for _, i, (move, _) in self.hand_actions(hand) if move == Action.FOLD)
            if len(folded) < self.players - 1:
                showdown_round = \
                    BettingRound.PREFLOP if len(flop) == 0 else \
                    BettingRound.FLOP if len(turn) == 0 else    \
                    BettingRound.TURN if len(river) == 0 else   \
                    BettingRound.RIVER
                showdown_string = ''.join(
                    f'  "p{i+1} sm {self._hands[hand][i][0]}{self._hands[hand][i][1]}",\n'
                    for i in range(self.players)
                    if i not in folded
                )
            else:
                showdown_round = None
                showdown_string = ''

            for r, actions in zip(iter(BettingRound), self.actions_by_round(hand)):
                if r == BettingRound.PREFLOP:
                    f.write(f'  # {r.name}\n')
                    # deal hands
                    for i, hole in enumerate(self._hands[hand]):
                        f.write(f'  "d dh p{i+1} {hole[0]}{hole[1]}",\n')
                else:
                    try:
                        if r == BettingRound.FLOP:
                            cards = (board[0], board[1], board[2])
                        elif r == BettingRound.TURN:
                            cards = (board[3],)
                        elif r == BettingRound.RIVER:
                            cards = (board[4],)
                    except IndexError:
                        break

                    f.write(f'  # {r.name}\n')
                    f.write(f'  "d db {''.join(str(c) for c in cards)}",\n')

                for a in actions:
                    f.write(f'  {action_str(a)}\n')

                if showdown_round == r:
                    f.write(showdown_string)

            f.write(']\n')

    def __str__(self) -> str:
        out = ''

        for i, (hand, cards, results) in enumerate(zip(self._hands, self.cards, self.results)):
            rounds = self.actions_by_round(i)
            out += 'Hands: ' + str(hand) + '\n'

            card_idx = 0
            for r, actions in zip(iter(BettingRound), rounds):
                if len(actions) == 0 and len(cards[card_idx:]) == 0:
                    continue

                out += '\n' + r.name + '\n'

                if r != BettingRound.PREFLOP:
                    ncards = 3 if r == BettingRound.FLOP else 1
                    out += f'New Cards: {cards[card_idx:card_idx + ncards]}\n'
                    card_idx += ncards
                else:
                    out += f'P{actions[0][1]} posts small blind (${actions[0][2][1]})\n'
                    amt = actions[0][2][1] + actions[1][2][1]
                    out += f'P{actions[1][1]} posts big blind (${amt})\n'

                    actions = actions[2:]

                for action in actions:
                    out += f'P{action[1]} {action[2][0].to_str(action[2][1])}\n'

            out += '\n'
            for result in results:
                winners = ', '.join(map(str, result[1]))
                desc = hands.to_str(result[2]) if result[2] > 0 else 'others folding'
                out += f'Players [{winners}] win ${result[0]} with {desc}\n'
            out += '\n'

        return out[:-2]

    def __repr__(self) -> str:
        return self.__str__()
