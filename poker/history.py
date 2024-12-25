'''
Datastructure to store poker game history, works with Game from poker.game.
Stores and loads PHH file format.
'''
from dataclasses import dataclass
from typing import List, Optional, Tuple

from pip._vendor.tomli import load

from poker import hands
from poker.hands import Hand
from poker.util import Action, BettingStage, Card, count, reorder, same

Move = Tuple[Action, Optional[int]]

class PHHParseError(ValueError):
    '''Error parsing .phh file'''

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

# FIXME: replace buy_in with starting_chips
class GameHistory:
    '''Datastructure to store poker game history, works with Game from poker.game'''

    @staticmethod
    def import_phh(file: str) -> 'GameHistory':
        '''
        Construct GameHistory from .phh file.
        Does not handle ?? for holecards.
        '''
        def parse_cardstr(s: str) -> List[Card]:
            out = []
            while len(s) > 0:
                out.append(Card.new(s[:2]))
                s = s[2:]
            return out

        with open(file, 'rb') as f:
            data = load(f)

        if data['variant'] != 'NT':
            raise PHHParseError('Game variant not supported!')
        if any(a != 0 for a in data['antes']):
            raise PHHParseError('Nonzero antes not supported!')
        if data['min_bet'] != 0:
            raise PHHParseError('Nonzero min bet not supported!')

        out = GameHistory(
            len(data['antes']),
            buy_in=data['starting_stacks'][0],
            small_blind=data['blinds_or_straddles'][0],
            big_blind=data['blinds_or_straddles'][1]
        )
        out.hand_count = 1
        out.cards.append([])
        out._hands.append([None] * out.players)

        # keep track of pots for results
        fold_chips = [0]
        # FIXME: change with starting chips
        pots = [{p: out.big_blind for p in range(out.players)}]

        stage_it = iter(BettingStage)
        stage = next(stage_it)
        for action in data['actions']:
            actor, a_type, *args = action.split()

            if actor == 'd':
                if a_type == 'dh':
                    out._hands[-1][int(args[0][1])-1] = tuple(parse_cardstr(args[1]))
                elif a_type == 'db':
                    out.cards[-1] += parse_cardstr(args[0])
                    stage = next(stage_it)
                else:
                    raise PHHParseError('Invalid dealer action!')

                continue

            player = int(actor[1]) - 1
            if a_type == 'cbr':
                pots[-1][player] = max(pots[-1].values()) + int(args[0])

                out.actions.append(ActionEntry(stage, player, (Action.RAISE, int(args[0]))))
            elif a_type == 'cc':
                pots[-1][player] = max(pots[-1].values())

                out.actions.append(ActionEntry(stage, player, (Action.CALL, None)))
            elif a_type == 'f':
                # move chips to folded pot
                for i, p in enumerate(pots):
                    fold_chips[i] += p.pop(player, 0)

                out.actions.append(ActionEntry(stage, player, (Action.FOLD, None)))

        # split pot
        while not same(pots[-1].values()):
            max_bet = min(pots[-1].values())
            pots.append({})
            for pl, bet in pots[-2].items():
                if bet > max_bet:
                    pots[-2][pl] = max_bet
                    pots[-1][pl] = bet - max_bet

        out.end_hand()

        # one person + folded chips remaining
        if count(pots[0].keys()) == 1:
            winner = next(pots[0].keys())
            out.results[-1].append(ResultEntry(
                sum(c + sum(p.values()) for c, p in zip(fold_chips, pots)),
                [winner],
                None
            ))
        # create rankings
        else:
            rankings = sorted([
                (i, hands.evaluate([*out.cards[0], *out._hands[0][i]]))
                for i in pots[0].keys()
            ], key=lambda x: x[1], reverse=True)

            for c, p in zip(fold_chips, pots):
                pot_rankings = [r for r in rankings if r[0] in p.keys()]
                winners = [p for p, h in pot_rankings if h == pot_rankings[-1][1]]
                out.results[-1].append(ResultEntry(
                    c + sum(p.values()),
                    winners,
                    pot_rankings[-1][1]
                ))

        return out


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

    def start_chips(self, hand: int) -> List[int]:
        # FIXME: change after start chips is changed
        return [self.buy_in] * self.players

    ### FILE REPR ###

    def export_phh(self, file: str, hand: int=0):
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
            open(file, 'wb').close()
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
