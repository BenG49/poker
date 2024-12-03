from typing import List

from game import Game, Player, FOLD, RIVER
from util import Card

class Raiser(Player):
	def __init__(self, min_raise: int):
		self.min_raise = min_raise

	def move(self, game: Game, pl_hand: List[Card], pl_id: int):
		if game.betting_round() == RIVER:
			print(Player.own_best_hand(game, pl_hand))

		return max(max(game.bets()), self.min_raise) - Player.own_data(game, pl_id).live_bet

class Checker(Player):
	def move(self, game: Game, pl_hand: List[Card], pl_id: int):
		if game.betting_round() == RIVER:
			print(Player.own_best_hand(game, pl_hand))

		return max(game.bets()) - Player.own_data(game, pl_id).live_bet

class Folder(Player):
	def move(self, game: Game, pl_hand: List[Card], pl_id: int):
		return FOLD

class AllIn(Player):
	def move(self, game: Game, pl_hand: List[Card], pl_id: int):
		return Player.own_data(game, pl_id).chips
