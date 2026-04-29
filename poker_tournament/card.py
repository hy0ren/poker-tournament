"""Card and Deck classes for poker."""

import random
from typing import List

RANK_NAMES = {
    2: '2', 3: '3', 4: '4', 5: '5', 6: '6', 7: '7', 8: '8',
    9: '9', 10: 'T', 11: 'J', 12: 'Q', 13: 'K', 14: 'A',
}

SUIT_SYMBOLS = {'h': '♥', 'd': '♦', 'c': '♣', 's': '♠'}


class Card:
    """Represents a single playing card."""

    __slots__ = ('rank', 'suit')

    def __init__(self, rank: int, suit: str):
        """
        Args:
            rank: Integer 2–14 (11=Jack, 12=Queen, 13=King, 14=Ace).
            suit: One of 'h' (hearts), 'd' (diamonds), 'c' (clubs), 's' (spades).
        """
        self.rank = rank
        self.suit = suit

    def __repr__(self) -> str:
        return f"{RANK_NAMES[self.rank]}{SUIT_SYMBOLS[self.suit]}"

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Card)
                and self.rank == other.rank
                and self.suit == other.suit)

    def __hash__(self) -> int:
        return hash((self.rank, self.suit))


class Deck:
    """A standard 52-card deck."""

    def __init__(self):
        self.cards: List[Card] = [
            Card(r, s)
            for r in range(2, 15)
            for s in ('h', 'd', 'c', 's')
        ]
        self.shuffle()

    def shuffle(self) -> None:
        random.shuffle(self.cards)

    def deal(self, n: int = 1):
        """Deal n cards. Returns a single Card when n==1, else a list."""
        if n == 1:
            return self.cards.pop()
        return [self.cards.pop() for _ in range(n)]

    def __len__(self) -> int:
        return len(self.cards)
