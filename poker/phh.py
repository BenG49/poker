'''
Functions for reading from and exporting to .phh format.
All really messy, should be cleaned up.
'''

from typing import BinaryIO

from pip._vendor import tomli

from . import hands
from .game_data import Action, BettingStage, GameConfig, Pot
from .history import ActionEntry, GameHistory, ResultEntry
from .util import Card, count

class PHHParseError(ValueError):
    '''Error parsing .phh file'''

def load(file: BinaryIO) -> GameHistory:
    # pylint: disable=protected-access
    '''Construct GameHistory from .phh file.'''
    data = tomli.load(file)

    if data['variant'] not in ('NT', 'FT'):
        raise PHHParseError('Game variant not supported!')

    fixed = data['variant'] == 'FT'
    antes = data['antes']

    out = GameHistory(GameConfig(
        small_blind=data['blinds_or_straddles'][0],
        big_blind=data['blinds_or_straddles'][1],
        small_bet=data['small_bet'] if fixed else 0,
        big_bet=data['big_bet'] if fixed else 0,
        min_bet=0 if fixed else data['min_bet'],
        ante_amt=max(antes),
        ante_idx=GameConfig.get_ante_idx(antes)
    ))
    out.hand_count = 1
    out.cards.append([])
    out.chips.append(data['starting_stacks'])
    out.players = len(out.chips[0])
    out._hands.append([None] * out.players)
    if 'finishing_stacks' in data:
        out.chips.append(data['finishing_stacks'])

    # keep track of pots for results, init pot with antes and blinds
    pots = [Pot(sum(antes), dict(enumerate(data['blinds_or_straddles'])), out.cfg.big_blind)]

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
                pots[-1].collect_bets()
            else:
                raise PHHParseError('Invalid dealer action!')

            continue

        player = int(actor[1]) - 1
        if a_type == 'cbr':
            bet = int(args[0]) - pots[-1].bets.get(player, 0)
            amt_raised = bet - pots[-1].chips_to_call(player)
            pots[-1].add(player, bet)

            out.actions.append(ActionEntry(stage, player, (Action.RAISE, amt_raised)))
        elif a_type == 'cc':
            pots[-1].add(player, pots[-1].chips_to_call(player))

            out.actions.append(ActionEntry(stage, player, (Action.CALL, None)))
        elif a_type == 'f':
            for pot in pots:
                pot.fold(player)

            out.actions.append(ActionEntry(stage, player, (Action.FOLD, None)))

    # split pot into side pots
    pots += pots[-1].split()
    out.end_hand()

    # one person + folded chips remaining
    if count(pots[0].players()) == 1:
        out.results[-1].append(ResultEntry(
            sum(pot.total() for pot in pots),
            list(pots[0].players()),
            None
        ))
    # create rankings
    else:
        rankings = sorted([
            (i, hands.evaluate([*out.cards[0], *out._hands[0][i]]))
            for i in pots[0].players()
        ], key=lambda x: x[1])

        for pot in pots:
            pot_rankings = [r for r in rankings if r[0] in pot.players()]
            winners = [p for p, h in pot_rankings if h == pot_rankings[0][1]]
            out.results[-1].append(ResultEntry(
                pot.total(),
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
    match history.cfg.ante_idx:
        case 1:
            antes = [0] + [history.cfg.ante_amt] + [0] * (history.players - 2)
            if history.players == 2:
                antes = antes[::-1]
        case -1: antes = [0] * (history.players - 1) + [history.cfg.ante_amt]
        case  _: antes = [history.cfg.ante_amt] * history.players

    out = (
        f'variant = "{variant}"\n'
        f'antes = {antes}\n'
        f'blinds_or_straddles = {blinds}\n'
        # NOTE: includes both limits and min bet
        f'small_bet = {history.cfg.small_bet}\n'
        f'big_bet = {history.cfg.big_bet}\n'
        f'min_bet = {history.cfg.min_bet}\n'
        f'starting_stacks = {history.chips[hand]}\n'
        f'seats = {history.players}\n'
        f'hand = {hand+1}\n'
        'actions = [\n'
    )

    board = history.cards[hand]

    # showing holecards
    hand_a = history.hand_actions(hand)
    folded = set(a.player for a in hand_a if a.move[0] == Action.FOLD)
    if len(folded) < history.players - 1:
        hand_a_stages = (a.stage if a is not None else None for a in hand_a)
        showdown_stage = (
            BettingStage.PREFLOP if BettingStage.FLOP not in hand_a_stages else
            BettingStage.FLOP    if BettingStage.TURN not in hand_a_stages else
            BettingStage.TURN    if BettingStage.RIVER not in hand_a_stages else
            BettingStage.RIVER)
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

            bets = dict(enumerate(blinds))
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

            bets = {p: 0 for p in range(history.players)}

        for a in actions:
            if a.move[0] == Action.FOLD:
                a_type = 'f'
                bets[a.player] = 0
            elif a.move[0] == Action.CALL:
                a_type = 'cc'
                bets[a.player] = max(bets.values())
            else:
                raised_to = a.move[1] + max(bets.values())
                a_type = f'cbr {raised_to}'
                bets[a.player] = raised_to

            out += f'  "p{a.player+1} {a_type}",'

            if a.move[0] == Action.ALL_IN:
                out += ' # All-in'
            out += '\n'

        if showdown_stage == r:
            out += showdown_string

    return out + ']\n'
