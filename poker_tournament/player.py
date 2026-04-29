"""Player class wrapping a bot function."""

from typing import Callable, List

from .card import Card


class Player:
    """Represents a player seat at the table."""

    def __init__(self, name: str, stack: int, bot_func: Callable):
        self.name = name
        self.stack = stack
        self.bot_func = bot_func

        # Per-hand state (reset each hand)
        self.hole_cards: List[Card] = []
        self.current_bet: int = 0    # Chips committed in the current betting round
        self.total_bet: int = 0      # Chips committed across all rounds this hand
        self.folded: bool = False
        self.all_in: bool = False

    # ------------------------------------------------------------------
    # State management
    # ------------------------------------------------------------------

    def reset_for_hand(self) -> None:
        self.hole_cards = []
        self.current_bet = 0
        self.total_bet = 0
        self.folded = False
        self.all_in = False

    def reset_for_round(self) -> None:
        """Called at the start of each betting street (flop/turn/river)."""
        self.current_bet = 0

    def is_active(self) -> bool:
        """True when the player can still voluntarily act."""
        return not self.folded and not self.all_in and self.stack > 0

    # ------------------------------------------------------------------
    # Chip handling
    # ------------------------------------------------------------------

    def bet(self, amount: int) -> int:
        """Commit *amount* chips (capped at stack). Sets all_in if necessary."""
        amount = min(amount, self.stack)
        self.stack -= amount
        self.current_bet += amount
        self.total_bet += amount
        if self.stack == 0:
            self.all_in = True
        return amount

    def __repr__(self) -> str:
        return f"Player({self.name!r}, stack={self.stack})"
