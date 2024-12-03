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
		game = Game()
		game.add_player(bots.Raiser(2), 200)
		game.add_player(bots.Checker(), 150)
		game.add_player(bots.Folder(), 100)
		game.add_player(bots.AllIn(), 50)
		self.assertEqual(len(game.pldata), 4)

		self.assertEqual(list(map(lambda x: x.chips, game.pldata)), [200, 150, 100, 50])
	
	def test_side_hand(self):
		game = Game()
		game.add_player(bots.Raiser(2), 200)
		game.add_player(bots.Checker(), 150)
		game.add_player(bots.Folder(), 100)
		game.add_player(bots.AllIn(), 50)
		random.seed(27)
		game.step_hand()

		'''
		preflop
			bets: 50, 50, 2, 50
			chips: 150, 100, 98, 0
			pot: 152
		after flop
			bets: 2, 2, -, -
			chips: 148, 98, 98, 0
			main pot: 152
			side pot: 4
		after turn
			bets: 2, 2, -, -
			chips: 146, 96, 98, 0
			main pot: 152
			side pot: 8
		after river
			bets: 2, 2, -, -
			chips: 144, 94, 98, 0
			main pot: 152
			side pot: 12
		showdown:
			player 3 and player 0 split main pot
			player 0 wins side pot
		
		final balances:
			232, 94, 98, 76
		'''

		# player 3 and player 0 tie

		# self.assertEqual(list(map(lambda x: x.chips, game.pldata)), [232, 94, 98, 76])
	
	# test multiple side pots (two all in with different values)
	def test_side_hands(self):
		game = Game()
		game.add_player(bots.AllIn(), 10)
		game.add_player(bots.AllIn(), 20)
		game.add_player(bots.AllIn(), 100)
		random.seed(107)
		game.step_hand()

		'''
		preflop
			bets: 10, 20, 100
			chips: 0, 0, 0
			main pot: 30
			side pot: 20
			side pot: 80
		showdown:
			tie
		
		final balances:
			10, 20, 100
		'''

		self.assertEqual(list(map(lambda x: x.chips, game.pldata)), [10, 20, 100])

	# test bet higher than another player's chips, then all in
	def test_side_hands2(self):
		game = Game()
		game.add_player(bots.AllIn(), 20)
		game.add_player(bots.AllIn(), 10)
		game.add_player(bots.AllIn(), 100)
		random.seed(107)
		game.step_hand()

		'''
		preflop
			bets: 20, 10, 100
			chips: 0, 0, 0
			main pot: 30
			side pot: 20
			side pot: 80
		showdown:
			tie
		
		final balances:
			20, 10, 100
		'''

		self.assertEqual(list(map(lambda x: x.chips, game.pldata)), [20, 10, 100])

if __name__ == '__main__':
	unittest.main()
