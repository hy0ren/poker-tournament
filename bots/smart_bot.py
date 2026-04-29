"""
smart_bot.py — Example poker bot using basic hand-strength heuristics.

Strategy:
  - Pre-flop: raise with premium hands, call with decent hands, fold trash.
  - Post-flop: bet/raise proportionally to hand strength.
  - Always consider pot odds before calling.
"""

BOT_NAME = "SmartBot"

# ---------------------------------------------------------------------------
# Hand-strength helpers (no external imports needed)
# ---------------------------------------------------------------------------

RANK_MAP = {r: r for r in range(2, 15)}   # rank is already an int 2–14

# Pre-flop hole-card scores (0–10, higher = stronger).
# Based on simplified Chen formula / hand ranking tables.
def _preflop_score(hole_cards):
    """Return a 0–10 score for two hole cards."""
    r1, r2 = sorted([c.rank for c in hole_cards], reverse=True)
    suited = hole_cards[0].suit == hole_cards[1].suit
    gap = r1 - r2

    score = 0.0

    # High-card value
    score += r1 / 2.0

    # Pair bonus
    if r1 == r2:
        score += max(r1 / 2.0, 5)

    # Suited bonus
    if suited:
        score += 2

    # Connector / gap penalty
    if r1 != r2:
        if gap == 0:
            pass  # already handled as pair
        elif gap == 1:
            score += 1
        elif gap == 2:
            score -= 1
        elif gap == 3:
            score -= 2
        else:
            score -= max(4, gap - 3)

    # Low-card penalty
    if r2 < 8 and r1 != r2:
        score -= 1

    return max(0.0, min(10.0, score))


def _hand_strength(hole_cards, community_cards):
    """
    Return a rough hand-strength estimate (0.0–1.0) using the current cards.
    Uses a simplified rank based on pair/flush/straight potential.
    """
    all_cards = hole_cards + community_cards
    if len(all_cards) < 5:
        # Pre-flop / early street: use preflop score
        return _preflop_score(hole_cards) / 10.0

    # Count best possible hand features
    ranks = [c.rank for c in all_cards]
    suits = [c.suit for c in all_cards]
    from collections import Counter
    rank_counts = Counter(ranks)
    suit_counts = Counter(suits)

    freq = sorted(rank_counts.values(), reverse=True)

    # Flush draw or made flush
    max_suit = max(suit_counts.values())

    # Straight detection (rough)
    unique_ranks = sorted(set(ranks))
    max_consec = _max_consecutive(unique_ranks)

    if freq[0] >= 4:
        return 0.97   # Four of a kind
    if freq[0] == 3 and freq[1] == 2:
        return 0.93   # Full house
    if max_suit >= 5:
        return 0.88   # Flush
    if max_consec >= 5:
        return 0.82   # Straight
    if freq[0] == 3:
        return 0.72   # Three of a kind
    if freq[0] == 2 and freq[1] == 2:
        return 0.60   # Two pair
    if freq[0] == 2:
        pair_rank = max(r for r, c in rank_counts.items() if c == 2)
        return 0.35 + pair_rank / 100   # One pair (higher pair = stronger)
    # High card
    high = max(ranks)
    return 0.10 + high / 200


def _max_consecutive(sorted_unique):
    """Return the longest run of consecutive ranks in a sorted list."""
    if not sorted_unique:
        return 0
    best = current = 1
    for i in range(1, len(sorted_unique)):
        if sorted_unique[i] == sorted_unique[i - 1] + 1:
            current += 1
            best = max(best, current)
        else:
            current = 1
    return best


# ---------------------------------------------------------------------------
# Bot entry point
# ---------------------------------------------------------------------------

def decide(game_state):
    hole_cards = game_state['hole_cards']
    community_cards = game_state['community_cards']
    pot = game_state['pot']
    call_amount = game_state['call_amount']
    stack = game_state['stack']
    my_bet = game_state['my_bet']
    big_blind = game_state['big_blind']
    round_name = game_state['round']

    strength = _hand_strength(hole_cards, community_cards)

    # ---- Pot odds ----
    # Only call if expected value is positive.
    # pot_odds = call_amount / (pot + call_amount)  → break-even equity needed
    if call_amount > 0:
        pot_odds = call_amount / (pot + call_amount)
    else:
        pot_odds = 0.0

    # ---- Decision logic ----
    if round_name == 'preflop':
        score = _preflop_score(hole_cards)
        if score >= 8:          # Premium: AA, KK, QQ, AK, AQ suited …
            raise_to = min(4 * big_blind + my_bet, stack + my_bet)
            return ('raise', raise_to)
        if score >= 6:          # Strong hand → call or small raise
            if call_amount == 0:
                raise_to = min(2 * big_blind, stack + my_bet)
                return ('raise', raise_to)
            return ('call', 0)
        if score >= 4:          # Marginal → call if pot odds are reasonable
            if call_amount <= big_blind:
                return ('call', 0)
            return ('fold', 0)
        # Weak hand
        return ('fold', 0) if call_amount > 0 else ('check', 0)

    # Post-flop decisions
    if strength >= 0.85:        # Very strong hand → raise big
        raise_to = min(int(pot * 0.75) + my_bet, stack + my_bet)
        raise_to = max(raise_to, game_state['min_raise'])
        if stack > call_amount:
            return ('raise', raise_to)
        return ('call', 0)

    if strength >= 0.60:        # Good hand → bet or call reasonable amounts
        if call_amount == 0:
            raise_to = min(int(pot * 0.5) + my_bet, stack + my_bet)
            raise_to = max(raise_to, game_state['min_raise'])
            if stack > 0:
                return ('raise', raise_to)
        if strength > pot_odds + 0.10:
            return ('call', 0)
        return ('fold', 0)

    if strength >= 0.35:        # Mediocre hand → cheap call only
        if call_amount == 0:
            return ('check', 0)
        if strength > pot_odds + 0.05:
            return ('call', 0)
        return ('fold', 0)

    # Weak hand
    if call_amount == 0:
        return ('check', 0)
    return ('fold', 0)
