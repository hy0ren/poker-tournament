"""Player state used by the game engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, List

from .card import Card


@dataclass
class Player:
    name: str
    stack: int
    bot_func: Callable
    hole_cards: List[Card] = field(default_factory=list)
    current_bet: int = 0
    total_bet: int = 0
    folded: bool = False
    all_in: bool = False

    def reset_for_hand(self) -> None:
        self.hole_cards = []
        self.current_bet = 0
        self.total_bet = 0
        self.folded = False
        self.all_in = False

    def reset_for_street(self) -> None:
        self.current_bet = 0

    def can_act(self) -> bool:
        return self.stack > 0 and not self.folded and not self.all_in

    def commit(self, amount: int) -> int:
        """Move chips from this player's stack into the pot."""
        amount = max(0, min(int(amount), self.stack))
        self.stack -= amount
        self.current_bet += amount
        self.total_bet += amount
        if self.stack == 0:
            self.all_in = True
        return amount

    def public_state(self, reveal_cards: bool = True) -> dict:
        return {
            "name": self.name,
            "stack": self.stack,
            "bet": self.current_bet,
            "total_bet": self.total_bet,
            "folded": self.folded,
            "all_in": self.all_in,
            "cards": [card.to_dict() for card in self.hole_cards] if reveal_cards else [],
        }
