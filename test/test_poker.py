'''
Unit testing for util.py and game.py
'''
from os import remove
import os
import unittest
import random

from agents import bots
from poker import phh
from poker.game_data import GameConfig
from poker.hands import evaluate, Hand
from poker.util import Card, count, same
from poker.game import Action, Game

class TestUtils(unittest.TestCase):
    def test_same(self):
        '''Test same method'''
        self.assertTrue(same([1, 1, 1]))
        self.assertFalse(same([1, 1, 0]))

    def test_count(self):
        '''Test count method'''
        self.assertEqual(count(map(lambda x: x**2, [0, 1, 2])), 3)

class TestLUT(unittest.TestCase):
    def test_coverage(self):
        '''Make sure all hand ranks are in LUT'''
        unsuited = Hand.UNSUITED.values()
        suited = Hand.SUITED.values()
        for i in range(1, Hand.HAND_COUNT + 1):
            self.assertTrue(i in unsuited or i in suited)

class TestHand(unittest.TestCase):
    def test_hand_ranks(self):
        '''Test ranking hands'''
        hand_ranks = [
            evaluate(Card.new('Tc7h4dKc2s')),
            evaluate(Card.new('KcKh7d2c5s')),
            evaluate(Card.new('KcKh7d7c5s')),
            evaluate(Card.new('KcKhKd7c5s')),
            evaluate(Card.new('Ac2h3d4c5s')),
            evaluate(Card.new('KcQc9c8c2c')),
            evaluate(Card.new('KcKhKd7c7s')),
            evaluate(Card.new('6s6d6h6cKs')),
            evaluate(Card.new('2s3s4s5s6s')),
            evaluate(Card.new('ThJhQhKhAh'))
        ]

        self.assertEqual(hand_ranks, [
            6926,
            3752,
            2662,
            1728,
            1609,
            884,
            185,
            108,
            9,
            1
        ])

    def test_highest_hand(self):
        '''Test finding highest hand from 7 card hand'''
        self.assertEqual(evaluate(Card.new('ThJhQhKhAh')),
            evaluate(Card.new('ThJhQhKhAh2sTs')),
            'Found the wrong highest hand!')


class TestGame(unittest.TestCase):
    # preflop
    #     bets: 100, 100, 2, 50
    #     chips: 100, 50, 98, 0
    #     pot: 152
    #     side pot: 100
    # after flop
    #     bets: 2, 2, -, -
    #     chips: 98, 48, 98, 0
    #     main pot: 152
    #     side pot: 104
    # after turn
    #     bets: 2, 2, -, -
    #     chips: 96, 46, 98, 0
    #     main pot: 152
    #     side pot: 108
    # after river
    #     bets: 2, 2, -, -
    #     chips: 94, 44, 98, 0
    #     main pot: 152
    #     side pot: 112
    # showdown:
    #     player 3 and player 0 split main pot
    #     player 0 wins side pot
    #
    # final balances:
    #     282, 44, 98, 76
    def test_side_hand(self):
        '''Test side pots'''
        game = Game(200, GameConfig.nl(2))
        game.add_player(bots.Raiser(2))
        game.add_player(bots.Checker())
        game.pl_data[-1].chips = 150
        game.add_player(bots.Folder())
        game.pl_data[-1].chips = 100
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 50
        random.seed(9)
        game.step_hand()

        # player 3 and player 0 tie

        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [282, 44, 98, 76])

    # test multiple side pots (two all in with different values)
    # preflop
    #     bets: 10, 20, 100
    #     chips: 0, 0, 0
    #     main pot: 30
    #     side pot: 20
    #     side pot: 80
    # showdown:
    #     tie
    #
    # final balances:
    #     10, 20, 100
    def test_side_hands(self):
        '''Test multiple side pots'''
        game = Game(100, GameConfig.nl(2))
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 10
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 20
        game.add_player(bots.AllIn())
        random.seed(12)
        game.step_hand()

        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [10, 20, 100])

    # test bet higher than another player's chips, then all in
    # preflop
    #     bets: 20, 10, 100
    #     chips: 0, 0, 0
    #     main pot: 30
    #     side pot: 20
    #     side pot: 80
    # showdown:
    #     tie
    #
    # final balances:
    #     20, 10, 100
    def test_side_hands2(self):
        '''Test side pots'''
        game = Game(100, GameConfig.nl(2))
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 20
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 10
        game.add_player(bots.AllIn())
        random.seed(12)
        game.step_hand()

        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [20, 10, 100])

    def test_all_fold(self):
        '''Test all players instantly folding'''
        game = Game(100, GameConfig.nl(2))
        game.add_player(bots.Folder())
        game.add_player(bots.Folder())
        game.add_player(bots.Folder())
        game.step_hand()

        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [100, 99, 101])

    def test_gen_nl_moves(self):
        '''Test move generation for No-limit Holdem games'''
        game = Game(10, GameConfig.nl(2))
        game.add_player()
        game.add_player()
        game.init_hand()
        self.assertEqual(game.get_moves(0), [
            (Action.FOLD, None),
            (Action.CALL, None),   # 1 chip
            (Action.RAISE, 1),     # 2 chips
            (Action.RAISE, 2),     # 3 chips
            (Action.RAISE, 3),     # 4 chips
            (Action.RAISE, 4),     # 5 chips
            (Action.RAISE, 5),     # 6 chips
            (Action.RAISE, 6),     # 7 chips
            (Action.RAISE, 7),     # 8 chips
            (Action.ALL_IN, None), # 9 chips
        ])

        game = Game(2, GameConfig.nl(2))
        game.add_player()
        game.add_player()
        game.init_hand()
        self.assertEqual(game.get_moves(0), [
            (Action.FOLD, None),
            (Action.CALL, None), # 1 chip
        ])

        game = Game(3, GameConfig.nl(2))
        game.add_player()
        game.add_player()
        game.init_hand()
        self.assertEqual(game.get_moves(0), [
            (Action.FOLD, None),
            (Action.CALL, None),   # 1 chip
            (Action.ALL_IN, None), # 2 chips
        ])

        game = Game(4, GameConfig.nl(2))
        game.add_player()
        game.add_player()
        game.init_hand()
        self.assertEqual(game.get_moves(0), [
            (Action.FOLD, None),
            (Action.CALL, None),   # 1 chip
            (Action.RAISE, 1),     # 2 chips
            (Action.ALL_IN, None), # 3 chips
        ])

        game = Game(6, GameConfig.nl(2))
        game.add_player()
        game.pl_data[-1].chips = 10
        game.add_player()
        game.init_hand()
        game.accept_move(Action.ALL_IN)
        self.assertEqual(game.get_moves(1), [
            (Action.FOLD, None),
            (Action.ALL_IN, None),
        ])

    def test_gen_fl_moves(self):
        '''Test move generation for Fixed-limit Holdem games'''
        cfg = GameConfig(0, 0, 4, 8)

        game = Game(8, cfg)
        game.add_player()
        game.add_player()
        game.init_hand()
        self.assertEqual(game.get_moves(0), [
            (Action.FOLD, None),
            (Action.CALL, None),
            (Action.RAISE, 4)
        ])

        # all in == fixed limit raise
        game = Game(8, cfg)
        game.add_player()
        game.add_player()
        game.init_hand()
        game.accept_move(Action.RAISE, 4)
        self.assertEqual(game.get_moves(1), [
            (Action.FOLD, None),
            (Action.CALL, None),  # 4 chips
            (Action.ALL_IN, None) # 8 chips
        ])

        # all in == fixed limit raise
        game = Game(8, cfg)
        game.add_player()
        game.add_player()
        game.init_hand()
        game.accept_move(Action.RAISE, 4)
        self.assertEqual(game.get_moves(1), [
            (Action.FOLD, None),
            (Action.CALL, None),  # 4 chips
            (Action.ALL_IN, None) # 8 chips
        ])

        # lots of all ins
        game = Game(4, cfg)
        game.add_player()
        game.add_player()
        game.init_hand()
        game.accept_move(Action.ALL_IN)
        self.assertEqual(game.get_moves(1), [
            (Action.FOLD, None),
            (Action.CALL, None),
        ])

        # complete all in
        game = Game(8, cfg)
        game.add_player()
        game.pl_data[0].chips = 2
        game.add_player()
        game.init_hand()
        game.accept_move(Action.ALL_IN)
        self.assertEqual(game.get_moves(1), [
            (Action.FOLD, None),
            (Action.CALL, None), # 2 chips
            (Action.RAISE, 4)    # 6 chips
        ])

        # raise limits
        game = Game(8, GameConfig(0, 0, 1, 2))
        game.add_player()
        game.add_player()
        game.add_player()
        game.init_hand()
        game.accept_move(Action.RAISE, 1) # P0
        game.accept_move(Action.RAISE, 1) # P1
        game.accept_move(Action.RAISE, 1) # P2
        game.accept_move(Action.RAISE, 1) # P0
        game.accept_move(Action.RAISE, 1) # P1
        self.assertEqual(game.get_moves(2), [
            (Action.FOLD, None),
            (Action.CALL, None),
        ])

    def test_allin_blinds(self):
        '''Make sure all players call big blind even if big blind player has to go all in'''
        game = Game(4, GameConfig.nl(2))
        game.add_player(bots.Checker()) # sb
        game.add_player(bots.Checker()) # bb
        game.pl_data[-1].chips = 1
        game.init_hand()
        game.step_move()
        self.assertEqual(game.pl_data[0].chips, 2)
        self.assertEqual(game.pl_data[1].chips, 0)

    def test_uneven_split(self):
        '''Test distributing odd chips'''
        # p1 puts one chip in and folds
        # p0 and p2 put two chips in and tie, odd chip
        game = Game(2, GameConfig.nl(0))
        game.add_player()
        game.add_player()
        game.add_player()
        random.seed(12)   # all players tie
        game.init_hand()
        game.accept_move(Action.RAISE, 1)
        game.accept_move(Action.CALL)
        game.accept_move(Action.CALL)
        # flop
        game.accept_move(Action.ALL_IN)
        game.accept_move(Action.FOLD)
        game.accept_move(Action.CALL)

        # button is 0, first player after button is 1
        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [2, 1, 3])

    def test_antes(self):
        '''Test that antes are not bets'''
        game = Game(4, GameConfig(0, 0, 0, 0, 0, 1, -1))
        game.add_player()
        game.add_player()
        game.add_player()
        game.init_hand()
        game.accept_move(Action.CALL)

        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [3, 4, 4])

class TestHistory(unittest.TestCase):
    def test_import_export(self):
        # pylint: disable=protected-access
        '''Test exporting and importing game history as phh file'''
        game = Game(1000, GameConfig.nl(20))
        game.add_player(bots.HandValueBetter())
        game.add_player(bots.Checker())
        random.seed(12)
        game.step_hand()

        with open('__test.phh', 'w', encoding='utf-8') as f:
            f.write(phh.dump(game.history))
        with open('__test.phh', 'rb') as f:
            imported = phh.load(f)

        self.assertEqual(game.history.players, imported.players)
        self.assertEqual(game.history.cfg, imported.cfg)

        self.assertEqual(game.history.actions, imported.actions)
        self.assertEqual(game.history.cards, imported.cards)
        self.assertEqual(game.history._hands, imported._hands)
        self.assertEqual(game.history.results, imported.results)
        self.assertEqual(game.history.chips, imported.chips)

        remove('__test.phh')

    def test_replays(self):
        '''Load .phh hands, test that they replay correctly'''
        for fname in os.listdir('data/wsop/'):
            with open('data/wsop/' + fname, 'rb') as f:
                try:
                    if fname != '02-53-09.phh': continue
                    hist = phh.load(f)
                    replay = Game.replay(hist)
                    while True:
                        try:
                            g = next(replay)
                        except StopIteration:
                            break

                    # verify replayed chips if finishing_stacks was included in file
                    if len(hist.chips) > 1:
                        self.assertTrue(hist.chips[1], list(p.chips for p in g.pl_data))
                except phh.PHHParseError as e:
                    print(f'{fname} FAILED:', e)

if __name__ == '__main__':
    unittest.main()
