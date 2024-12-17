'''
Datastructure to store poker game history, works with Game from poker.game.
'''
from typing import List, Optional, Tuple

from poker.hand import Hand, print_hand
from poker.util import Action, BettingRound, Card

Move = Tuple[Action, Optional[int]]

class GameHistory:
    '''Datastructure to store poker game history, works with Game from poker.game'''

    # round, player id, move
    # None is end of round specifier
    ActionTuple = Optional[Tuple[BettingRound, int, Move]]
    # pot id, pot total, winner list, best hand (-1 if win from fold)
    WinTuple = Tuple[int, int, List[int], Hand]

    @staticmethod
    def action_str(action: ActionTuple) -> str:
        '''Converts action tuple to string'''
        return f'P{action[1]} {action[2][0].to_str(action[2][1])}'

    @staticmethod
    def results_str(results: WinTuple) -> str:
        '''Converts results tuple to string'''
        winners = ', '.join(map(str, results[2]))
        result = print_hand(results[3]) if results[3] > 0 else 'others folding'
        return f'Players [{winners}] win (Pot {results[0]}, ${results[1]}) with {result}'

    def __init__(self):
        self.actions: List[GameHistory.ActionTuple] = []
        self.cards: List[Card] = []
        # flattened list of hands
        # ex. 2 players with [Kh, Kc] and [Qh, 4s]
        # [Kh, Kc, Qh, 4s]
        self._hands: List[List[Card]] = []
        self.results: List[GameHistory.WinTuple] = []

    def add_action(self, bround: BettingRound, player: int, action: Move):
        '''Add player action to history'''
        self.actions.append((
            bround,
            player,
            action
        ))

    def deal(self, cards) -> Card | List[Card]:
        '''Add dealt card to history'''
        if isinstance(cards, Card):
            self.cards.append(cards)
        else:
            self.cards.extend(cards)
        return cards

    def add_hands(self, hands: List[List[Card]]):
        '''Add new round's hands to history'''
        self._hands.append(tuple(card for hand in hands for card in hand))

    def end_hand(self):
        '''Call before calling add_result, after the end of the hand, before processing pots'''
        self.results.append([])
        self.actions.append(None)

    def add_result(self, pot: int, pot_amt: int, winners: List[int], top_hand: Hand):
        '''Add result for each pot processed'''
        self.results[-1].append((pot, pot_amt, winners, top_hand))

    def __str__(self) -> str:
        out = ''

        card_idx = 0
        move_idx = 0
        last_round = BettingRound.RIVER
        for hand, result in zip(self._hands, self.results):
            out += 'Hands: ' + str(list(zip(hand[::2], hand[1::2]))) + '\n'

            while True:
                if move_idx >= len(self.actions):
                    break
                if self.actions[move_idx] is None:
                    move_idx += 1
                    break
                # new betting round
                if last_round != self.actions[move_idx][0]:
                    last_round = self.actions[move_idx][0]
                    out += '\n' + last_round.name + '\n'

                    if last_round != BettingRound.PREFLOP:
                        ncards = 3 if last_round == BettingRound.FLOP else 1
                        out += f'New Cards: {self.cards[card_idx:card_idx + ncards]}\n'
                        card_idx += ncards

                out += GameHistory.action_str(self.actions[move_idx]) + '\n'
                move_idx += 1

            out += '\n'
            for pot in result:
                out += GameHistory.results_str(pot) + '\n'
            out += '\n'

        return out[:-2]

    def __repr__(self) -> str:
        return self.__str__()
