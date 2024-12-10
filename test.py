'''
Unit testing for util.py and game.py
'''
import unittest
import random

from util import same, Hand, Card
from game import Game
import bots

class TestSame(unittest.TestCase):
    def test_same(self):
        self.assertTrue(same([1, 1, 1]))
        self.assertFalse(same([1, 1, 0]))

class TestHand(unittest.TestCase):
    def test_hand_ranks(self):
        hands = [
            Hand([Card.make('Tc'), Card.make('7h'), Card.make('4d'), Card.make('Kc'), Card.make('2s')]),
            Hand([Card.make('Kc'), Card.make('Kh'), Card.make('7d'), Card.make('2c'), Card.make('5s')]),
            Hand([Card.make('Kc'), Card.make('Kh'), Card.make('7d'), Card.make('7c'), Card.make('5s')]),
            Hand([Card.make('Kc'), Card.make('Kh'), Card.make('Kd'), Card.make('7c'), Card.make('5s')]),
            Hand([Card.make('Ac'), Card.make('2h'), Card.make('3d'), Card.make('4c'), Card.make('5s')]),
            Hand([Card.make('Kc'), Card.make('Qc'), Card.make('9c'), Card.make('8c'), Card.make('2c')]),
            Hand([Card.make('Kc'), Card.make('Kh'), Card.make('Kd'), Card.make('7c'), Card.make('7s')]),
            Hand([Card.make('6s'), Card.make('6d'), Card.make('6h'), Card.make('6c'), Card.make('Ks')]),
            Hand([Card.make('2s'), Card.make('3s'), Card.make('4s'), Card.make('5s'), Card.make('6s')]),
            Hand([Card.make('Th'), Card.make('Jh'), Card.make('Qh'), Card.make('Kh'), Card.make('Ah')])
        ]

        for h in range(len(hands) - 1):
            self.assertLess(hands[h], hands[h+1])

    def test_highest_hand(self):
        self.assertEqual(Hand([Card.make('Th'), Card.make('Jh'), Card.make('Qh'), Card.make('Kh'), Card.make('Ah')]),
            Hand.get_highest_hand(Card.make('Th'), Card.make('Jh'), Card.make('Qh'), Card.make('Kh'), Card.make('Ah'), Card.make('2s'), Card.make('Ts')),
            'Found the wrong highest hand!')


class TestGame(unittest.TestCase):
    def test_player_data(self):
        game = Game(200)
        game.add_player(bots.Raiser(2))
        game.add_player(bots.Checker())
        game.pl_data[-1].chips = 150
        game.add_player(bots.Folder())
        game.pl_data[-1].chips = 100
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 50
        self.assertEqual(len(game.pl_data), 4)

        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [200, 150, 100, 50])

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
        game = Game(200)
        game.add_player(bots.Raiser(2))
        game.add_player(bots.Checker())
        game.pl_data[-1].chips = 150
        game.add_player(bots.Folder())
        game.pl_data[-1].chips = 100
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 50
        random.seed(27)
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
        game = Game(100)
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 10
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 20
        game.add_player(bots.AllIn())
        random.seed(107)
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
        game = Game(100)
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 20
        game.add_player(bots.AllIn())
        game.pl_data[-1].chips = 10
        game.add_player(bots.AllIn())
        random.seed(107)
        game.step_hand()

        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [20, 10, 100])

    def test_all_fold(self):
        game = Game(100)
        game.add_player(bots.Folder())
        game.add_player(bots.Folder())
        game.add_player(bots.Folder())
        game.step_hand()

        self.assertEqual(list(map(lambda x: x.chips, game.pl_data)), [100, 99, 101])

if __name__ == '__main__':
    unittest.main()
