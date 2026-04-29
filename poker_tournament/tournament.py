"""Tournament runner."""

from typing import Callable, Dict, List, Optional, Tuple

from .game import PokerGame
from .player import Player


class Tournament:
    """
    Runs a poker tournament between a set of bots.

    Two modes
    ---------
    elimination (default)
        All players share one table.  Play continues until one player
        holds all the chips.  Players are ranked by the order they busted.

    fixed
        Play exactly ``num_hands`` hands and rank by final chip count.
    """

    def __init__(
        self,
        bots: List[Tuple[str, Callable]],
        starting_chips: int = 1000,
        small_blind: int = 10,
        big_blind: int = 20,
        mode: str = 'elimination',
        num_hands: int = 1000,
        verbose: bool = True,
    ):
        if len(bots) < 2:
            raise ValueError("A tournament needs at least 2 bots.")
        if mode not in ('elimination', 'fixed'):
            raise ValueError("mode must be 'elimination' or 'fixed'.")

        self.bots = bots
        self.starting_chips = starting_chips
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.mode = mode
        self.num_hands = num_hands
        self.verbose = verbose

        self._players: List[Player] = []
        self._standings: List[Dict] = []   # Filled as players bust out

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def run(self) -> List[Dict]:
        """
        Run the tournament and return the final standings.

        Each entry in the returned list is a dict::

            {
                'rank':   int,       # 1 = winner
                'name':   str,
                'chips':  int,       # chips at end of tournament
                'hands_played': int,
            }
        """
        self._players = [
            Player(name, self.starting_chips, func)
            for name, func in self.bots
        ]
        self._standings = []

        game = PokerGame(
            self._players,
            small_blind=self.small_blind,
            big_blind=self.big_blind,
            verbose=self.verbose,
        )

        if self.mode == 'elimination':
            self._run_elimination(game)
        else:
            self._run_fixed(game)

        return self._final_standings(game.hand_number)

    # ------------------------------------------------------------------
    # Run modes
    # ------------------------------------------------------------------

    def _run_elimination(self, game: PokerGame) -> None:
        bust_order: List[Player] = []

        while True:
            active = [p for p in self._players if p.stack > 0]
            if len(active) <= 1:
                break

            result = game.play_hand()
            if result is None:
                break

            # Check for newly busted players (stack == 0 after the hand)
            for p in self._players:
                if p.stack == 0 and p not in bust_order:
                    bust_order.append(p)
                    if self.verbose:
                        print(f"\n  *** {p.name} has been eliminated! ***")

        # Record standings (worst → best, then reverse for rank assignment)
        total = len(self._players)
        for rank, p in enumerate(reversed(bust_order), start=2):
            self._standings.append({
                'rank': total - len(bust_order) + rank - 1,
                'name': p.name,
                'chips': 0,
            })

        # The player(s) still with chips are the winner(s)
        winners = [p for p in self._players if p.stack > 0]
        for i, w in enumerate(winners, start=1):
            self._standings.insert(0, {
                'rank': i,
                'name': w.name,
                'chips': w.stack,
            })

    def _run_fixed(self, game: PokerGame) -> None:
        for _ in range(self.num_hands):
            active = [p for p in self._players if p.stack > 0]
            if len(active) < 2:
                break
            result = game.play_hand()
            if result is None:
                break

    # ------------------------------------------------------------------
    # Standings helper
    # ------------------------------------------------------------------

    def _final_standings(self, hands_played: int) -> List[Dict]:
        if self.mode == 'fixed':
            # Rank by final chip count
            ranked = sorted(self._players, key=lambda p: p.stack, reverse=True)
            self._standings = [
                {'rank': i + 1, 'name': p.name, 'chips': p.stack}
                for i, p in enumerate(ranked)
            ]

        # Attach hands_played to every entry (same for the whole tournament)
        for entry in self._standings:
            entry['hands_played'] = hands_played

        return self._standings

    def print_results(self, standings: Optional[List[Dict]] = None) -> None:
        """Pretty-print the final standings table."""
        if standings is None:
            standings = self._standings
        print("\n" + "=" * 55)
        print("  FINAL STANDINGS")
        print("=" * 55)
        print(f"  {'Rank':<6} {'Name':<25} {'Chips':>8}")
        print("-" * 55)
        for entry in standings:
            print(
                f"  {entry['rank']:<6} {entry['name']:<25} {entry['chips']:>8}"
            )
        print("=" * 55)
        print(f"  Total hands played: {standings[0].get('hands_played', '?')}")
        print("=" * 55)
