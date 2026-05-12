"""Playing cards and deck utilities for the workshop tournament."""

from __future__ import annotations

import random
from dataclasses import dataclass
from typing import List, Optional

RANK_LABELS = {
    2: "2",
    3: "3",
    4: "4",
    5: "5",
    6: "6",
    7: "7",
    8: "8",
    9: "9",
    10: "T",
    11: "J",
    12: "Q",
    13: "K",
    14: "A",
}

SUIT_SYMBOLS = {
    "h": "♥",
    "d": "♦",
    "c": "♣",
    "s": "♠",
}

SUITS = tuple(SUIT_SYMBOLS.keys())


@dataclass(frozen=True)
class Card:
    """A single standard playing card.

    Ranks are integers from 2 through 14, where 14 is an ace. Suits are the
    one-letter strings ``h``, ``d``, ``c``, and ``s``.
    """

    rank: int
    suit: str

    def __post_init__(self) -> None:
        if self.rank not in RANK_LABELS:
            raise ValueError(f"Invalid card rank: {self.rank!r}")
        if self.suit not in SUIT_SYMBOLS:
            raise ValueError(f"Invalid card suit: {self.suit!r}")

    @property
    def label(self) -> str:
        return RANK_LABELS[self.rank]

    @property
    def symbol(self) -> str:
        return SUIT_SYMBOLS[self.suit]

    @property
    def color(self) -> str:
        return "red" if self.suit in {"h", "d"} else "black"

    def to_dict(self) -> dict:
        return {
            "rank": self.rank,
            "suit": self.suit,
            "label": self.label,
            "symbol": self.symbol,
            "text": str(self),
            "color": self.color,
        }

    def __str__(self) -> str:
        return f"{self.label}{self.symbol}"

    def __repr__(self) -> str:
        return str(self)


class Deck:
    """A shuffled 52-card deck."""

    def __init__(self, rng: Optional[random.Random] = None):
        self.rng = rng or random.Random()
        self.cards: List[Card] = [
            Card(rank, suit)
            for rank in range(2, 15)
            for suit in SUITS
        ]
        self.shuffle()

    def shuffle(self) -> None:
        self.rng.shuffle(self.cards)

    def deal(self, count: int = 1):
        if count < 1:
            raise ValueError("count must be at least 1")
        if count > len(self.cards):
            raise ValueError("Cannot deal more cards than remain in the deck")
        if count == 1:
            return self.cards.pop()
        return [self.cards.pop() for _ in range(count)]

    def __len__(self) -> int:
        return len(self.cards)
