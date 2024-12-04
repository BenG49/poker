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
            Hand([Card.make('T♣'), Card.make('7♥'), Card.make('4♦'), Card.make('K♣'), Card.make('2♠')]),
            Hand([Card.make('K♣'), Card.make('K♥'), Card.make('7♦'), Card.make('2♣'), Card.make('5♠')]),
            Hand([Card.make('K♣'), Card.make('K♥'), Card.make('7♦'), Card.make('7♣'), Card.make('5♠')]),
            Hand([Card.make('K♣'), Card.make('K♥'), Card.make('K♦'), Card.make('7♣'), Card.make('5♠')]),
            Hand([Card.make('A♣'), Card.make('2♥'), Card.make('3♦'), Card.make('4♣'), Card.make('5♠')]),
            Hand([Card.make('K♣'), Card.make('Q♣'), Card.make('9♣'), Card.make('8♣'), Card.make('2♣')]),
            Hand([Card.make('K♣'), Card.make('K♥'), Card.make('K♦'), Card.make('7♣'), Card.make('7♠')]),
            Hand([Card.make('6♠'), Card.make('6♦'), Card.make('6♥'), Card.make('6♣'), Card.make('K♠')]),
            Hand([Card.make('2♠'), Card.make('3♠'), Card.make('4♠'), Card.make('5♠'), Card.make('6♠')]),
            Hand([Card.make('T♥'), Card.make('J♥'), Card.make('Q♥'), Card.make('K♥'), Card.make('A♥')])
        ]

        for h in range(len(hands) - 1):
            self.assertLess(hands[h], hands[h+1])

    def test_highest_hand(self):
        self.assertEqual(Hand([Card.make('T♥'), Card.make('J♥'), Card.make('Q♥'), Card.make('K♥'), Card.make('A♥')]),
            Hand.get_highest_hand(Card.make('T♥'), Card.make('J♥'), Card.make('Q♥'), Card.make('K♥'), Card.make('A♥'), Card.make('2♠'), Card.make('T♠')),
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

if __name__ == '__main__':
    unittest.main()
