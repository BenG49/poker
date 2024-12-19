'''
Datastructure to store poker game history, works with Game from poker.game.
'''
from typing import List, Optional, Tuple

from poker import hands
from poker.hands import Hand
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
        result = hands.to_str(results[3]) if results[3] > 0 else 'others folding'
        return f'Players [{winners}] win (Pot {results[0]}, ${results[1]}) with {result}'

    def __init__(self, buy_in, big_blind, small_blind):
        self.buy_in = buy_in
        self.big_blind = big_blind
        self.small_blind = small_blind

        self.actions: List[GameHistory.ActionTuple] = []
        self.cards: List[Card] = []
        self._hands: List[List[Tuple[Card]]] = []
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

    def add_hands(self, round_hands: List[List[Card]]):
        '''Add new round's hands to history'''
        self._hands.append(round_hands)

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
            start_move = move_idx
            out += 'Hands: ' + str(hand) + '\n'

            while True:
                action = self.actions[move_idx]

                if move_idx >= len(self.actions):
                    break
                if action is None:
                    move_idx += 1
                    break
                # new betting round
                if last_round != action[0]:
                    last_round = action[0]
                    out += '\n' + last_round.name + '\n'

                    if last_round != BettingRound.PREFLOP:
                        ncards = 3 if last_round == BettingRound.FLOP else 1
                        out += f'New Cards: {self.cards[card_idx:card_idx + ncards]}\n'
                        card_idx += ncards

                if move_idx - start_move < 2 and self.big_blind > 0 and self.small_blind > 0:
                    if move_idx == start_move:
                        out += f'P{action[1]} posts small blind (${action[2][1]})'
                    else:
                        amt = action[2][1] + self.actions[start_move][2][1]
                        out += f'P{action[1]} posts big blind (${amt})'
                else:
                    out += f'P{action[1]} {action[2][0].to_str(action[2][1])}'
                out += '\n'
                move_idx += 1

            out += '\n'
            for pot in result:
                out += GameHistory.results_str(pot) + '\n'
            out += '\n'

        return out[:-2]

    def __repr__(self) -> str:
        return self.__str__()
