"""Small Texas Hold'em hand evaluator.

The evaluator checks every 5-card combination from the cards supplied and
returns a tuple that can be compared directly: higher tuples are better hands.
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from typing import Iterable, List, Sequence, Tuple

from .card import Card

HAND_NAMES = {
    8: "Straight Flush",
    7: "Four of a Kind",
    6: "Full House",
    5: "Flush",
    4: "Straight",
    3: "Three of a Kind",
    2: "Two Pair",
    1: "One Pair",
    0: "High Card",
}


def evaluate_hand(cards: Sequence[Card]) -> Tuple[int, ...]:
    """Return the best 5-card poker score from 5 to 7 cards."""
    if len(cards) < 5:
        raise ValueError(f"Need at least 5 cards, got {len(cards)}")
    if len(cards) > 7:
        raise ValueError(f"Expected at most 7 cards, got {len(cards)}")

    best: Tuple[int, ...] = ()
    for five_cards in combinations(cards, 5):
        score = _score_five(five_cards)
        if not best or score > best:
            best = score
    return best


def hand_name(score: Sequence[int]) -> str:
    return HAND_NAMES.get(score[0], "Unknown")


def _score_five(cards: Iterable[Card]) -> Tuple[int, ...]:
    ranks = sorted((card.rank for card in cards), reverse=True)
    suits = [card.suit for card in cards]
    counts = Counter(ranks)
    groups = sorted(counts, key=lambda rank: (counts[rank], rank), reverse=True)
    frequencies = sorted(counts.values(), reverse=True)

    flush = len(set(suits)) == 1
    straight_high = _straight_high(ranks)

    if flush and straight_high:
        return (8, straight_high)
    if frequencies == [4, 1]:
        return (7, groups[0], groups[1])
    if frequencies == [3, 2]:
        return (6, groups[0], groups[1])
    if flush:
        return (5, *ranks)
    if straight_high:
        return (4, straight_high)
    if frequencies == [3, 1, 1]:
        return (3, groups[0], groups[1], groups[2])
    if frequencies == [2, 2, 1]:
        return (2, groups[0], groups[1], groups[2])
    if frequencies == [2, 1, 1, 1]:
        return (1, groups[0], groups[1], groups[2], groups[3])
    return (0, *ranks)


def _straight_high(ranks: List[int]) -> int:
    unique = sorted(set(ranks), reverse=True)
    if len(unique) != 5:
        return 0
    if unique[0] - unique[-1] == 4:
        return unique[0]
    if set(unique) == {14, 5, 4, 3, 2}:
        return 5
    return 0
