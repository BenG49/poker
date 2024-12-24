'''
Datastructure to store poker game history, works with Game from poker.game.
Stores and loads PHH file format.
'''
from dataclasses import dataclass
from typing import List, Optional, Tuple

from poker import hands
from poker.hands import Hand
from poker.util import Action, BettingStage, Card, reorder

Move = Tuple[Action, Optional[int]]

@dataclass
class ActionEntry:
    '''Entry for an action'''
    stage: BettingStage
    player: int
    move: Move

@dataclass
class ResultEntry:
    '''Entry for each result of a round (one per pot)'''
    pot_total: int
    winners: List[int]
    # None if win from fold
    winning_hand: Optional[Hand]
    chips: List[int]

class GameHistory:
    '''Datastructure to store poker game history, works with Game from poker.game'''

    def __init__(self, players, buy_in, big_blind, small_blind):
        # assumes players all start with buy_in chips
        self.players = players
        self.buy_in = buy_in
        self.big_blind = big_blind
        self.small_blind = small_blind

        self.actions: List[Optional[ActionEntry]] = []
        self.cards:   List[List[Card]] = []
        self._hands:  List[List[Tuple[Card]]] = []
        self.results: List[List[ResultEntry]] = []

        self.hand_count = 0

    ### ADD TO HISTORY ###

    def add_hands(self, round_hands: List[Tuple[Card]]):
        '''Add new round's hands to history'''
        self.hand_count += 1
        self.cards.append([])
        self._hands.append(reorder(
            lambda idx: self.to_history_index(self.hand_count - 1, idx),
            round_hands
        ))

    def add_action(self, stage: BettingStage, player: int, action: Move):
        '''Add player action to history'''
        self.actions.append(ActionEntry(
            stage,
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
        self.results[-1].append(ResultEntry(
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

    def hand_actions(self, hand: int) -> List[Optional[ActionEntry]]:
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

    def actions_by_stage(self, hand: int) -> Tuple[list, list, list, list]:
        '''Split actions for hand into preflop, flop, turn, and river betting stages'''
        lists = { r: [] for r in iter(BettingStage) }
        for action in self.hand_actions(hand):
            lists[action.stage].append(action)
        return (lists.get(r) for r in iter(BettingStage))

    def start_chips(self, hand: int) -> List[int]:
        if hand > 0:
            return self.results[hand - 1][-1].chips
        return [self.buy_in] * self.players

    ### FILE REPR ###

    def export(self, file: str, hand: int=0):
        '''Export hand to .phh file'''
        # TODO: add .phh extension, export to file-1, file-2 for hand 1, hand 2, if more than one hand

        def action_str(action: ActionEntry) -> str:
            if action.move[0] == Action.FOLD:
                out = 'f'
            elif action.move[0] == Action.CALL:
                out = 'cc'
            else:
                out = f'cbr {action.move[1]}'
            out = f'"p{action.player+1} {out}",'

            if action.move[0] == Action.ALL_IN:
                out += ' # All-in'
            return out

        # there are not enough hands to export requested hand
        if self.hand_count < hand + 1:
            open(file, 'w', encoding='utf-8').close()
            return

        with open(file, 'w', encoding="utf-8") as f:
            f.write('variant = "NT"\n')
            f.write(f'antes = {[0] * self.players}\n')
            blinds = [self.small_blind, self.big_blind] + [0] * (self.players - 2)
            f.write(f'blinds_or_straddles = {blinds}\n')
            f.write('min_bet = 0\n')
            f.write(f'starting_stacks = {self.start_chips(hand)}\n')
            f.write(f'seats = {self.players}\n')
            f.write(f'hand = {hand+1}\n')
            f.write('actions = [\n')

            board = self.cards[hand]
            _, flop, turn, river = self.actions_by_stage(hand)

            # showing holecards
            folded = set(a.player for a in self.hand_actions(hand) if a.move[0] == Action.FOLD)
            if len(folded) < self.players - 1:
                showdown_stage = \
                    BettingStage.PREFLOP if len(flop) == 0 else \
                    BettingStage.FLOP if len(turn) == 0 else    \
                    BettingStage.TURN if len(river) == 0 else   \
                    BettingStage.RIVER
                showdown_string = ''.join(
                    f'  "p{i+1} sm {self._hands[hand][i][0]}{self._hands[hand][i][1]}",\n'
                    for i in range(self.players)
                    if i not in folded
                )
            else:
                showdown_stage = None
                showdown_string = ''

            for r, actions in zip(iter(BettingStage), self.actions_by_stage(hand)):
                if r == BettingStage.PREFLOP:
                    f.write(f'  # {r.name}\n')
                    # deal hands
                    for i, hole in enumerate(self._hands[hand]):
                        f.write(f'  "d dh p{i+1} {hole[0]}{hole[1]}",\n')
                else:
                    try:
                        if r == BettingStage.FLOP:
                            cards = (board[0], board[1], board[2])
                        elif r == BettingStage.TURN:
                            cards = (board[3],)
                        elif r == BettingStage.RIVER:
                            cards = (board[4],)
                    except IndexError:
                        break

                    f.write(f'  # {r.name}\n')
                    f.write(f'  "d db {''.join(str(c) for c in cards)}",\n')

                for a in actions:
                    f.write(f'  {action_str(a)}\n')

                if showdown_stage == r:
                    f.write(showdown_string)

            f.write(']\n')

    def __str__(self) -> str:
        out = ''

        for i, (hand, cards, results) in enumerate(zip(self._hands, self.cards, self.results)):
            out += 'Hands: ' + str(hand) + '\n'

            card_idx = 0
            for r, actions in zip(iter(BettingStage), self.actions_by_stage(i)):
                if len(actions) == 0 and len(cards[card_idx:]) == 0:
                    continue

                out += '\n' + r.name + '\n'

                if r != BettingStage.PREFLOP:
                    ncards = 3 if r == BettingStage.FLOP else 1
                    out += f'New Cards: {cards[card_idx:card_idx + ncards]}\n'
                    card_idx += ncards
                elif self.big_blind > 0 and self.small_blind > 0:
                    if self.players == 2:
                        bb = 1
                        sb = 2
                    else:
                        sb = 1
                        bb = 2

                    out += f'P{sb} posts small blind (${self.small_blind})\n'
                    out += f'P{bb} posts big blind (${self.big_blind})\n'

                for action in actions:
                    out += f'P{action.player+1} {action.move[0].to_str(action.move[1])}\n'

            out += '\n'
            for result in results:
                winners = ', '.join(str(w+1) for w in result.winners)
                desc = hands.to_str(result.winning_hand) if \
                    result.winning_hand is not None else \
                    'others folding'
                out += f'Players [{winners}] win ${result.pot_total} with {desc}\n'
            out += '\n'

        return out[:-2]

    def __repr__(self) -> str:
        return self.__str__()
