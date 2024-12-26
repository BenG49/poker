'''
Unit testing for util.py and game.py
'''
from os import remove
import unittest
import random

from agents import bots
from poker import phh
from poker.hands import evaluate, Hand
from poker.util import Card, count, same
from poker.game import Game

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
    #     bets: 52, 52, 2, 50
    #     chips: 148, 98, 98, 0
    #     pot: 152
    #     side pot: 4
    # after flop
    #     bets: 2, 2, -, -
    #     chips: 146, 96, 98, 0
    #     main pot: 152
    #     side pot: 8
    # after turn
    #     bets: 2, 2, -, -
    #     chips: 144, 94, 98, 0
    #     main pot: 152
    #     side pot: 12
    # after river
    #     bets: 2, 2, -, -
    #     chips: 142, 92, 98, 0
    #     main pot: 152
    #     side pot: 16
    # showdown:
    #     player 3 and player 0 split main pot
    #     player 0 wins side pot
    #
    # final balances:
    #     234, 92, 98, 76
    def test_side_hand(self):
        '''Test side pots'''
        game = Game(200, 2)
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

        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [234, 92, 98, 76])

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
        game = Game(100, 2)
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
        game = Game(100, 2)
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
        game = Game(100, 2)
        game.add_player(bots.Folder())
        game.add_player(bots.Folder())
        game.add_player(bots.Folder())
        game.step_hand()

        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [100, 99, 101])

    def test_gen_moves(self):
        '''Test valid move generation'''
        game = Game(100, 2)
        game.add_player(bots.Checker())
        game.add_player(bots.Checker())
        game.init_hand()
        self.assertEqual(len(game.get_moves(0)), 100)

        game = Game(2, 2)
        game.add_player(bots.Checker())
        game.add_player(bots.Checker())
        game.init_hand()
        self.assertEqual(len(game.get_moves(0)), 2)

        game = Game(3, 2)
        game.add_player(bots.Checker())
        game.add_player(bots.Checker())
        game.init_hand()
        self.assertEqual(len(game.get_moves(0)), 3)

        game = Game(4, 2)
        game.add_player(bots.Checker())
        game.add_player(bots.Checker())
        game.init_hand()
        self.assertEqual(len(game.get_moves(0)), 4)

    def test_allin_blinds(self):
        '''Make sure all players call big blind even if big blind player has to go all in'''
        game = Game(4, 2)
        game.add_player(bots.Checker()) # sb
        game.add_player(bots.Checker()) # bb
        game.pl_data[-1].chips = 1
        game.init_hand()
        game.step_move()
        self.assertEqual(game.pl_data[0].chips, 2)
        self.assertEqual(game.pl_data[1].chips, 0)

class TestHistory(unittest.TestCase):
    def test_import_export(self):
        '''Test exporting and importing game history as phh file'''
        game = Game(1000, 20)
        game.add_player(bots.HandValueBetter())
        game.add_player(bots.Checker())
        random.seed(12)
        game.step_hand()

        with open('__test.phh', 'w', encoding='utf-8') as f:
            f.write(phh.dump(game.history))
        with open('__test.phh', 'rb') as f:
            imported = phh.load(f)

        self.assertEqual(game.history.players, imported.players)
        self.assertEqual(game.history.small_blind, imported.small_blind)
        self.assertEqual(game.history.big_blind, imported.big_blind)

        self.assertEqual(game.history.actions, imported.actions)
        self.assertEqual(game.history.cards, imported.cards)
        self.assertEqual(game.history._hands, imported._hands)
        self.assertEqual(game.history.results, imported.results)
        self.assertEqual(game.history.chips, imported.chips)

        remove('__test.phh')

if __name__ == '__main__':
    unittest.main()
