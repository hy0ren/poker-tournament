"""Tournament runner for poker bots."""

from __future__ import annotations

import random
from typing import Any, Callable, Dict, List, Optional, Tuple

from .game import PokerGame
from .player import Player

MAX_BOTS = 23


class Tournament:
    """Run a table of bots for a fixed number of hands or until one remains."""

    def __init__(
        self,
        bots: List[Tuple[str, Callable]],
        starting_chips: int = 1000,
        small_blind: int = 10,
        big_blind: int = 20,
        mode: str = "fixed",
        num_hands: int = 25,
        verbose: bool = True,
        seed: Optional[int] = None,
    ):
        if len(bots) < 2:
            raise ValueError("A tournament needs at least two bots.")
        if len(bots) > MAX_BOTS:
            raise ValueError(f"A tournament can seat at most {MAX_BOTS} bots.")
        if starting_chips < 2:
            raise ValueError("starting_chips must be at least 2.")
        if small_blind < 1 or big_blind <= small_blind:
            raise ValueError("small_blind must be positive and below big_blind.")
        if mode not in {"fixed", "elimination"}:
            raise ValueError("mode must be 'fixed' or 'elimination'.")
        if num_hands < 1:
            raise ValueError("num_hands must be at least 1.")

        self.bots = bots
        self.starting_chips = starting_chips
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.mode = mode
        self.num_hands = num_hands
        self.verbose = verbose
        self.seed = seed

        self.players: List[Player] = []
        self.hands: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.standings: List[Dict[str, Any]] = []

    def run(self) -> List[Dict[str, Any]]:
        self.players = [
            Player(name, self.starting_chips, decide)
            for name, decide in self._unique_bots()
        ]
        self.hands = []
        self.events = []
        self.standings = []

        game = PokerGame(
            self.players,
            small_blind=self.small_blind,
            big_blind=self.big_blind,
            verbose=self.verbose,
            rng=random.Random(self.seed),
        )

        while self._should_continue():
            result = game.play_hand()
            if result is None:
                break
            self.hands.append(result)
            self.events.extend(result["events"])

        self.standings = self._build_standings()
        self.events.append(
            {
                "type": "tournament_complete",
                "message": "Tournament complete.",
                "standings": self.standings,
                "snapshot": self._final_snapshot(),
            }
        )
        return self.standings

    def print_results(self, standings: Optional[List[Dict[str, Any]]] = None) -> None:
        rows = standings or self.standings
        print()
        print("Final standings")
        print("-" * 46)
        print(f"{'Rank':<6}{'Bot':<24}{'Chips':>10}")
        print("-" * 46)
        for row in rows:
            print(f"{row['rank']:<6}{row['name']:<24}{row['chips']:>10}")
        print("-" * 46)
        hands = rows[0]["hands_played"] if rows else 0
        print(f"Hands played: {hands}")

    def to_payload(self) -> Dict[str, Any]:
        return {
            "standings": self.standings,
            "hands": self.hands,
            "events": self.events,
            "hands_played": len(self.hands),
            "config": {
                "mode": self.mode,
                "starting_chips": self.starting_chips,
                "small_blind": self.small_blind,
                "big_blind": self.big_blind,
                "num_hands": self.num_hands,
                "seed": self.seed,
                "bots": [name for name, _ in self._unique_bots()],
            },
        }

    def _should_continue(self) -> bool:
        active = [player for player in self.players if player.stack > 0]
        if len(active) < 2:
            return False
        if len(self.hands) >= self.num_hands:
            return False
        if self.mode == "fixed":
            return True
        return len(active) > 1

    def _build_standings(self) -> List[Dict[str, Any]]:
        ranked = sorted(self.players, key=lambda player: (-player.stack, player.name))
        return [
            {
                "rank": index + 1,
                "name": player.name,
                "chips": player.stack,
                "hands_played": len(self.hands),
                "status": "active" if player.stack > 0 else "out",
            }
            for index, player in enumerate(ranked)
        ]

    def _final_snapshot(self) -> Dict[str, Any]:
        return {
            "hand_number": len(self.hands),
            "street": "complete",
            "dealer": "",
            "pot": 0,
            "community_cards": [],
            "players": [player.public_state() for player in self.players],
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
        }

    def _unique_bots(self) -> List[Tuple[str, Callable]]:
        seen: Dict[str, int] = {}
        unique = []
        for name, decide in self.bots:
            count = seen.get(name, 0) + 1
            seen[name] = count
            display_name = name if count == 1 else f"{name} {count}"
            unique.append((display_name, decide))
        return unique
