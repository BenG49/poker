'''
Unit testing for util.py and game.py
'''
import unittest
import random

from poker.util import Hand, Card, it_len, same
from poker.game import Game
import agents.bots as bots

class TestUtils(unittest.TestCase):
    def test_same(self):
        self.assertTrue(same([1, 1, 1]))
        self.assertFalse(same([1, 1, 0]))

    def test_itlen(self):
        self.assertEqual(it_len(map(lambda x: x**2, [0, 1, 2])), 3)

class TestLUT(unittest.TestCase):
    def test_coverage(self):
        values = Hand.LOOKUP.values()
        for i in range(1, Hand.HAND_COUNT + 1):
            self.assertIn(i, values)

class TestHand(unittest.TestCase):
    def test_hand_ranks(self):
        hands = [
            Hand([Card.new('Tc'), Card.new('7h'), Card.new('4d'), Card.new('Kc'), Card.new('2s')]),
            Hand([Card.new('Kc'), Card.new('Kh'), Card.new('7d'), Card.new('2c'), Card.new('5s')]),
            Hand([Card.new('Kc'), Card.new('Kh'), Card.new('7d'), Card.new('7c'), Card.new('5s')]),
            Hand([Card.new('Kc'), Card.new('Kh'), Card.new('Kd'), Card.new('7c'), Card.new('5s')]),
            Hand([Card.new('Ac'), Card.new('2h'), Card.new('3d'), Card.new('4c'), Card.new('5s')]),
            Hand([Card.new('Kc'), Card.new('Qc'), Card.new('9c'), Card.new('8c'), Card.new('2c')]),
            Hand([Card.new('Kc'), Card.new('Kh'), Card.new('Kd'), Card.new('7c'), Card.new('7s')]),
            Hand([Card.new('6s'), Card.new('6d'), Card.new('6h'), Card.new('6c'), Card.new('Ks')]),
            Hand([Card.new('2s'), Card.new('3s'), Card.new('4s'), Card.new('5s'), Card.new('6s')]),
            Hand([Card.new('Th'), Card.new('Jh'), Card.new('Qh'), Card.new('Kh'), Card.new('Ah')])
        ]

        assert hands == [
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
        ]

    def test_highest_hand(self):
        self.assertEqual(Hand([Card.new('Th'), Card.new('Jh'), Card.new('Qh'), Card.new('Kh'), Card.new('Ah')]),
            Hand.get_best_hand(Card.new('Th'), Card.new('Jh'), Card.new('Qh'), Card.new('Kh'), Card.new('Ah'), Card.new('2s'), Card.new('Ts')),
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
