'''
Functions for reading from and exporting to .phh format.
All really messy, should be cleaned up.
'''

from typing import BinaryIO

from pip._vendor import tomli

from . import hands
from .game_data import Action, BettingStage, GameConfig
from .history import ActionEntry, GameHistory, ResultEntry
from .util import Card, count, same

class PHHParseError(ValueError):
    '''Error parsing .phh file'''

def load(file: BinaryIO) -> GameHistory:
    # pylint: disable=protected-access
    '''Construct GameHistory from .phh file.'''
    data = tomli.load(file)

    if data['variant'] not in ('NT', 'FT'):
        raise PHHParseError('Game variant not supported!')
    if any(a != 0 for a in data['antes']):
        raise PHHParseError('Nonzero antes not supported!')

    fixed = data['variant'] == 'FT'

    if not fixed and data['min_bet'] != 0:
        raise NotImplementedError

    antes = data['antes']
    out = GameHistory(GameConfig(
        small_blind=data['blinds_or_straddles'][0],
        big_blind=data['blinds_or_straddles'][1],
        small_bet=data['small_bet'] if fixed else 0,
        big_bet=data['big_bet'] if fixed else 0,
        min_bet=0 if fixed else data['min_bet'],
        ante_amt=max(antes),
        # TODO: make this cover other cases
        ante_idx=None if same(antes) else (-1 if antes[-1] == max(antes) else 1)
    ))
    out.hand_count = 1
    out.cards.append([])
    out.chips.append(data['starting_stacks'])
    out.players = len(out.chips[0])
    out._hands.append([None] * out.players)
    if 'finishing_stacks' in data:
        out.chips.append(data['finishing_stacks'])

    # keep track of pots for results
    fold_chips = [0]
    pots = [{p: min(out.cfg.big_blind, out.chips[0][p]) for p in range(out.players)}]

    stage_it = iter(BettingStage)
    stage = next(stage_it)
    for action in data['actions']:
        actor, a_type, *args = action.split()

        if actor == 'd':
            if a_type == 'dh':
                h = [None if '?' in h else Card.new(h) for h in zip(args[1][0::2], args[1][1::2])]
                out._hands[0][int(args[0][1])-1] = tuple(h)
            elif a_type == 'db':
                card = Card.new(args[0])
                out.cards[0].extend([card] if isinstance(card, Card) else card)
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
        winner = next(iter(pots[0].keys()))
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
        ], key=lambda x: x[1])

        for c, p in zip(fold_chips, pots):
            pot_rankings = [r for r in rankings if r[0] in p.keys()]
            winners = [p for p, h in pot_rankings if h == pot_rankings[0][1]]
            out.results[-1].append(ResultEntry(
                c + sum(p.values()),
                winners,
                pot_rankings[0][1]
            ))

    return out

def dump(history: GameHistory, hand: int=0) -> str:
    # pylint: disable=protected-access
    '''Dump one hand's history to .phh file format'''

    # there are not enough hands to export requested hand
    if history.hand_count < hand + 1:
        return ''

    blinds = [history.cfg.small_blind, history.cfg.big_blind] + [0] * (history.players - 2)
    variant = 'FT' if history.cfg.is_limit() else 'NT'
    bet_limits = (
        f'small_bet = {history.cfg.small_bet}\nbig_bet = {history.cfg.big_bet}'
        if history.cfg.is_limit() else
        'min_bet = 0'
    )

    out = (
        f'variant = "{variant}"\n'
        f'antes = {[0] * history.players}\n'
        f'blinds_or_straddles = {blinds}\n'
        f'{bet_limits}\n'
        f'starting_stacks = {history.chips[hand]}\n'
        f'seats = {history.players}\n'
        f'hand = {hand+1}\n'
        'actions = [\n'
    )

    board = history.cards[hand]

    # showing holecards
    folded = set(a.player for a in history.hand_actions(hand) if a.move[0] == Action.FOLD)
    if len(folded) < history.players - 1:
        _, flop, turn, river = history.actions_by_stage(hand)
        showdown_stage = \
            BettingStage.PREFLOP if len(flop) == 0 else \
            BettingStage.FLOP if len(turn) == 0 else    \
            BettingStage.TURN if len(river) == 0 else   \
            BettingStage.RIVER
        showdown_string = ''.join(
            f'  "p{i+1} sm {history._hands[hand][i][0]}{history._hands[hand][i][1]}",\n'
            for i in range(history.players)
            if i not in folded
        )
    else:
        showdown_stage = None
        showdown_string = ''

    for r, actions in zip(iter(BettingStage), history.actions_by_stage(hand)):
        if r == BettingStage.PREFLOP:
            out += f'  # {r.name}\n'
            # deal hands
            for i, hole in enumerate(history._hands[hand]):
                out += f'  "d dh p{i+1} {hole[0]}{hole[1]}",\n'
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

            out += f'  # {r.name}\n'
            out += f'  "d db {''.join(str(c) for c in cards)}",\n'

        for a in actions:
            if a.move[0] == Action.FOLD:
                a_type = 'f'
            elif a.move[0] == Action.CALL:
                a_type = 'cc'
            else:
                a_type = f'cbr {a.move[1]}'

            out += f'  "p{a.player+1} {a_type}",'

            if a.move[0] == Action.ALL_IN:
                out += ' # All-in'
            out += '\n'

        if showdown_stage == r:
            out += showdown_string

    return out + ']\n'
