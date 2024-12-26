'''
Datastructure to store poker game history, works with Game from poker.game.
Stores and loads PHH file format.
'''
from dataclasses import dataclass
from typing import List, Optional, Tuple

from . import hands
from .hands import Hand
from .util import Action, BettingStage, Card, reorder

Move = Tuple[Action, Optional[int]]

@dataclass
class ActionEntry:
    '''Entry for an action'''
    stage: BettingStage
    player: int
    move: Move

    def __str__(self) -> str:
        return f'P{self.player} {self.move[0].to_str(self.move[1])}'
    def __repr__(self) -> str:
        return f'{self.stage.name} P{self.player} {self.move[0].to_str(self.move[1])}'

@dataclass
class ResultEntry:
    '''Entry for each result of a round (one per pot)'''
    pot_total: int
    winners: List[int]
    # None if win from fold
    winning_hand: Optional[Hand]

    def __str__(self) -> str:
        winners = ', '.join(str(w+1) for w in self.winners)
        desc = hands.to_str(self.winning_hand) if \
            self.winning_hand is not None else \
            'others folding'
        return f'Players [{winners}] win ${self.pot_total} with {desc}'

class GameHistory:
    '''Datastructure to store poker game history, works with Game from poker.game'''
    def __init__(self, big_blind, small_blind):
        self.players = -1
        self.big_blind = big_blind
        self.small_blind = small_blind

        self.chips:   List[List[int]] = []
        self.actions: List[Optional[ActionEntry]] = []
        self.cards:   List[List[Card]] = []
        self._hands:  List[List[Tuple[Card]]] = []
        self.results: List[List[ResultEntry]] = []

        self.hand_count = 0

    ### ADD TO HISTORY ###

    def __reorder_new_list(self, l: list) -> list:
        return reorder(lambda idx: self.to_history_index(self.hand_count - 1, idx), l)

    def init_hand(self, chips: List[int], round_hands: List[Tuple[Card]]):
        '''Add new round's hands to history'''
        self.players = len(chips)
        self.hand_count += 1
        self.cards.append([])
        self._hands.append(self.__reorder_new_list(round_hands))
        self.chips.append(self.__reorder_new_list(chips))

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

    def add_result(self, pot_amt: int, winners: List[int], top_hand: Hand):
        '''Add result for each pot processed'''
        self.results[-1].append(ResultEntry(
            pot_amt,
            [self.to_history_index(self.hand_count - 1, w) for w in winners],
            top_hand
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

    def actions_by_hand(self) -> List[List[Optional[ActionEntry]]]:
        '''Split actions into actions per hand'''
        out = [[] for _ in range(self.hand_count)]
        i = 0
        for a in self.actions:
            if a is None:
                i += 1
            else:
                out[i].append(a)
        return out

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
