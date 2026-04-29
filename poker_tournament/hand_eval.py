"""Texas Hold'em hand evaluator.

Evaluates the best 5-card hand from 5–7 cards and returns a comparable
score tuple — higher is better.
"""

from collections import Counter
from itertools import combinations
from typing import List, Tuple

from .card import Card

HAND_RANKS = {
    8: 'Straight Flush',
    7: 'Four of a Kind',
    6: 'Full House',
    5: 'Flush',
    4: 'Straight',
    3: 'Three of a Kind',
    2: 'Two Pair',
    1: 'One Pair',
    0: 'High Card',
}


def evaluate_hand(cards: List[Card]) -> Tuple:
    """Return the best-hand score tuple from 5–7 cards (higher = better)."""
    if len(cards) < 5:
        raise ValueError(f"Need at least 5 cards, got {len(cards)}")
    best: Tuple = ()
    for combo in combinations(cards, 5):
        score = _score_five(combo)
        if not best or score > best:
            best = score
    return best


def _score_five(cards) -> Tuple:
    """Score exactly 5 cards and return a comparable tuple."""
    ranks = sorted([c.rank for c in cards], reverse=True)
    suits = [c.suit for c in cards]

    is_flush = len(set(suits)) == 1

    # Straight detection
    is_straight = False
    straight_high = 0
    if len(set(ranks)) == 5 and ranks[0] - ranks[4] == 4:
        is_straight = True
        straight_high = ranks[0]
    elif set(ranks) == {14, 2, 3, 4, 5}:   # Wheel A-2-3-4-5
        is_straight = True
        straight_high = 5

    counts = Counter(ranks)
    # Sort groups: primary key = count (desc), secondary key = rank (desc)
    groups = sorted(counts.keys(), key=lambda r: (counts[r], r), reverse=True)
    freq = sorted(counts.values(), reverse=True)

    if is_straight and is_flush:
        return (8, straight_high)
    if freq == [4, 1]:
        return (7, groups[0], groups[1])
    if freq == [3, 2]:
        return (6, groups[0], groups[1])
    if is_flush:
        return (5, *ranks)
    if is_straight:
        return (4, straight_high)
    if freq == [3, 1, 1]:
        return (3, groups[0], groups[1], groups[2])
    if freq == [2, 2, 1]:
        return (2, groups[0], groups[1], groups[2])
    if freq == [2, 1, 1, 1]:
        return (1, groups[0], groups[1], groups[2], groups[3])
    return (0, *ranks)


def hand_name(score: Tuple) -> str:
    """Return the human-readable name for a hand score tuple."""
    return HAND_RANKS.get(score[0], 'Unknown')
