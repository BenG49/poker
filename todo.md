# TODO
- clean up util.Hand.\_\_init\_\_
- ~~use more iterator methods~~
- ~~separate deck into class~~
- ~~improve pot processing~~
	- ~~each player should store last pot~~
	- ~~pot method to fold player~~
	- ~~split() should only return max one pot~~
	- ~~separate current bets and previous rounds amounts~~
- ~~improve PlayerData~~
	- ~~store player id~~
	- ~~store player state (folded, active)~~
- ~~improve API of game~~
	- ~~instead of just int for move, return move type and value~~
	- ~~only game should be passed~~
- ~~convert from methods with while loops inside to state machine that you update by running .move~~
	- ~~step() method that just gets the move from one person~~
	- hand_running() - if not running, need to run init_hand()
- ~~convert hand to continuous numbers 1 to 7462~~
	- ~~add helper methods~~
	- ~~convert card to int~~
	- add equity calculation
- ~~raise x vs raise _to_ x~~
- add comprehensive tester
- bot testing suite
	- how should bots be tested?
		- dataset of hand histories?

## Bot
- Monte Carlo Counterfactual Regret Minimization
	- figure out what needs to be added to api to extend history, infoset
		- list all moves (all actions)
	```python
	class CFR:
		def walk_tree():
			...
	```
