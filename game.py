from abc import ABC, abstractmethod
from dataclasses import dataclass
from random import shuffle
from typing import List, Tuple

from util import same, Card, Hand

FOLD = -1

PREFLOP = 0
FLOP = 1
TURN = 2
RIVER = 3

class InvalidMoveError(ValueError): ...

@dataclass
class Pot:
	bets: List[int]
	pl_ids: List[int]

	def add(self, pl_id: int, chips: int):
		self.bets[self.pl_ids.index(pl_id)] += chips

	def chips(self) -> int:
		return sum(self.bets)

	# splits pot into side pots and returns list
	# NOTE: does not differentiate between folding and going all in, has same end effect
	def split(self) -> List:
		if same(self.bets):
			return [self]
		else:
			max_stake = min(self.bets)

			next_bets = []
			next_pl_ids = []

			for i, (bet, pl_id) in enumerate(zip(self.bets, self.pl_ids)):
				if bet == max_stake: continue

				next_pl_ids.append(pl_id)
				next_bets.append(bet - max_stake)
				self.bets[i] = max_stake
			
			return [self, *Pot(next_bets, next_pl_ids).split()]

	def __repr__(self) -> str:
		return self.__str__()
	def __str__(self) -> str:
		return f'${self.chips()} players [{", ".join(map(str, self.pl_ids))}]'

@dataclass
class PlayerData:
	chips: int
	live_bet: int

	def folded(self) -> bool:
		return self.live_bet == FOLD

	def active(self) -> bool:
		return not self.folded() and self.chips > 0

	def bet(self, amt: int):
		if amt > self.chips:
			raise InvalidMoveError

		self.chips -= amt
		self.live_bet += amt

class Player(ABC):
	#  -1: fold
	#   0: check
	# etc: bet/call/raise
	@abstractmethod
	def move(self, game, pl_hand: List[Card], pl_id: int) -> int:
		...
	
	def own_data(game, pl_id: int) -> PlayerData:
		return game.pldata[pl_id]

	def own_best_hand(game, pl_hand: List[Card]) -> Hand:
		return Hand.get_highest_hand(*game.community, *pl_hand)

class Game:
	def __init__(self, buy_in: int, bigblind: int = 2):
		# game state
		self.buy_in: int = buy_in
		self.bigblind: int = bigblind
		self.smlblind: int = bigblind // 2

		# game state
		self.button: int = 0
		self.pldata: List[PlayerData] = []
		self.community: List[Card] = []
		self.pots: List[Pot] = []

		### PRIVATE ###
		self.__hands: List[List[Card]] = []
		self.__players: List[Player] = []
		self.__deck: List[Card] = Card.gen_deck()
	
	def bet_round(self):
		# start past blinds if first betting round
		turn_id = self.pl_left(self.button, 3 if self.betting_round() == 0 else 1)
		# give everyone one turn
		moved = [False] * len(self.__players)
		
		# wait until all active players have matched bets
		while not all(moved) or not same([pl.live_bet for pl in self.pldata if pl.active()]):
			if self.pldata[turn_id].active():
				move = self.__players[turn_id].move(self, self.__hands[turn_id], turn_id)

				self.check_valid_bet(turn_id, move)

				if move == FOLD:
					self.pots[-1].add(turn_id, self.pldata[turn_id].live_bet)
					self.pldata[turn_id].live_bet = FOLD
				else:
					self.pldata[turn_id].bet(move)
			
			moved[turn_id] = True
			turn_id = self.pl_left(turn_id)
		
		# clear remaining bets into most up to date pot
		for pl_id, p in enumerate(self.pldata):
			if not p.folded() and p.live_bet > 0:
				self.pots[-1].add(pl_id, p.live_bet)
				p.live_bet = 0

		for p in self.pots.pop().split():
			self.pots.append(p)
	
	def step_hand(self):
		assert len(self.__players) > 1

		# reset
		self.community = []
		self.pots = [Pot([0]*len(self.__players), range(len(self.__players)))]
		self.__hands = [[] for _ in self.__players]
		for p in self.pldata:
			p.live_bet = 0
		
		# blinds
		if len(self.__players) == 2:
			small = self.button
			big = self.pl_left(self.button)
		else:
			small = self.pl_left(self.button)
			big = self.pl_left(self.button, 2)
		
		self.pldata[small].bet(self.smlblind)
		self.pldata[big].bet(self.bigblind)

		# deal hands
		shuffle(self.__deck)
		for _ in range(2):
			for h in [i % len(self.__hands) for i in range(small, small+len(self.__hands))]:
				self.__hands[h].append(self.__deck.pop())
		print('Hands:', self.__hands)

		for r in range(4):
			self.bet_round()

			# check if only one player remaining
			# or showdown
			if list(map(PlayerData.folded, self.pldata)).count(False) == 1 or \
			  r == 3:
				self.end_hand()
				break

			# deal
			if r != 3:
				self.__burn_card()
				for _ in range(3 if r == 0 else 1):
					self.community.append(self.__deck.pop())
		
			if r < 3:
				print('Community:', self.community)

		self.button = self.pl_right(self.button)
	
	def end_hand(self):
		def pl_id(t: Tuple[int, Hand]): return t[0]
		def hand(t: Tuple[int, Hand]): return t[1]

		rankings = self.__get_hand_rankings()
		for pot in self.pots:
			pot_hands = list(filter(lambda x: pl_id(x) in pot.pl_ids, rankings))
			winners = [pl_id(pl) for pl in pot_hands if hand(pl) == hand(pot_hands[-1])]
			win_value = pot.chips() // len(winners)
			remainder = pot.chips() % len(winners)

			if remainder != 0: raise NotImplementedError

			for winner in winners:
				self.pldata[winner].chips += win_value
	
	### MODIFIERS ###
	
	def add_player(self, player: Player):
		self.pldata.append(PlayerData(self.buy_in, 0))
		self.__players.append(player)

	def __burn_card(self):
		self.__deck.insert(0, self.__deck.pop())

	### NON-MODIFIER UTILS ###

	def __get_hand_rankings(self) -> List[Tuple[int, Hand]]:
		return sorted([
			(i, Hand.get_highest_hand(*self.community, *self.__hands[i]))
			for i in range(len(self.__players))
			if not self.pldata[i].folded()
		], key=lambda x: x[1])

	def betting_round(self) -> int:
		return {0: 0, 3: 1, 4: 2, 5: 3}[len(self.community)]
	
	def check_valid_bet(self, pl_id: int, bet: int):
		if bet == FOLD: return
		# all in
		if bet == self.pldata[pl_id].chips: return

		if bet > self.pldata[pl_id].chips:
			raise InvalidMoveError(f'Attempting to bet {bet} chips with only {self.pldata[pl_id].chips} available!')
		elif self.pldata[pl_id].live_bet + bet < max(self.bets()):
			raise InvalidMoveError('Bet too little to match current bet')

	def bets(self) -> List[int]:
		return list(map(lambda pl: pl.live_bet, self.pldata))

	def pl_left(self, pl_id: int, n: int = 1) -> int:
		return (pl_id + n) % len(self.__players)

	def pl_right(self, pl_id: int, n: int = 1) -> int:
		return (pl_id - n) % len(self.__players)
