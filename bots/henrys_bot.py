"""Henry's Bot: GTO-inspired poker AI with targeted bot exploitation."""

import random
from poker_tournament.hand_eval import evaluate_hand
from poker_tournament.card import Card

BOT_NAME = "Henry's Bot"
TIER = "advanced"
DESCRIPTION = ""

_MC_SAMPLES = 180
_rng = random.Random()

_DECK = [(rank, suit) for rank in range(2, 15) for suit in ("h", "d", "c", "s")]


def decide(game_state):
    active_opponents = sum(1 for p in game_state["players"] if not p["folded"])

    if _god_bot_active(game_state):
        return _exploit_god_bot(game_state, active_opponents)

    street = game_state["round"]
    if street == "preflop":
        return _preflop(game_state, active_opponents)
    return _postflop(game_state, active_opponents)


# ---------------------------------------------------------------------------
# GodBot exploitation
# ---------------------------------------------------------------------------

def _god_bot_active(game_state):
    return any(p["name"] == "GodBot" and not p["folded"] for p in game_state["players"])


def _god_bot_committed(game_state):
    """True when GodBot has bet > 0 this street — its _can_raise returns False."""
    for p in game_state["players"]:
        if p["name"] == "GodBot" and not p["folded"]:
            return p["bet"] > 0
    return False


def _exploit_god_bot(game_state, active_opponents):
    """
    Core exploit: GodBot's _can_raise checks my_bet == 0. Once it has committed
    chips (including posting BB preflop), it can never re-raise. We can barrel
    freely. GodBot also folds any hand where strength < pot_odds + 0.12, so
    overbetting (2x pot, pot_odds ~0.67) wipes out its entire medium range.
    """
    street = game_state["round"]
    hole = game_state["hole_cards"]
    community = game_state["community_cards"]
    call_amount = game_state["call_amount"]
    pot = game_state["pot"]
    big_blind = game_state["big_blind"]

    equity = (
        _preflop_strength(hole)
        if street == "preflop"
        else _mc_equity(hole, community, active_opponents)
    )

    god_locked = _god_bot_committed(game_state)

    if god_locked:
        # GodBot cannot re-raise. Exploit freely.
        if call_amount == 0:
            # Overbet: forces GodBot to need strength >= 0.79 to call.
            # Fold out its entire medium range (0.35–0.78).
            if equity >= 0.32 or _has_draw(hole, community):
                return "raise", _overbet(game_state)
            return "check", 0
        else:
            pot_odds = call_amount / (pot + call_amount)
            if equity >= pot_odds + 0.04:
                if _can_raise(game_state):
                    return "raise", _overbet(game_state)
                return "call", 0
            return "fold", 0
    else:
        # GodBot hasn't committed yet — play aggressively to get it to commit,
        # after which it loses its raise ability.
        if call_amount == 0:
            if equity >= 0.48:
                return "raise", _raise_to(game_state, equity)
            if equity >= 0.36 and _has_draw(hole, community) and _rng.random() < 0.45:
                return "raise", _raise_to(game_state, 0.50)
            return "check", 0

        pot_odds = call_amount / (pot + call_amount)

        if equity >= 0.68:
            if _can_raise(game_state):
                return "raise", _raise_to(game_state, equity)
            return "call", 0

        if equity >= pot_odds + 0.04:
            return "call", 0

        if call_amount <= big_blind and equity >= 0.26:
            return "call", 0

        return "fold", 0


def _overbet(game_state):
    """2x pot bet: forces GodBot to need 0.79+ strength to call."""
    pot = game_state["pot"]
    my_bet = game_state["my_bet"]
    big_blind = game_state["big_blind"]
    stack = game_state["stack"]
    target = my_bet + max(big_blind * 2, int(pot * 2.0))
    return min(target, my_bet + stack)


# ---------------------------------------------------------------------------
# Preflop (vs other bots)
# ---------------------------------------------------------------------------

def _preflop(gs, opp_count):
    hole = gs["hole_cards"]
    call_amount = gs["call_amount"]
    pot = gs["pot"]
    big_blind = gs["big_blind"]

    strength = _preflop_strength(hole)
    adjusted = strength - opp_count * 0.02

    if call_amount == 0:
        if adjusted >= 0.62:
            return "raise", _raise_to(gs, adjusted)
        if adjusted >= 0.42 and _rng.random() < 0.30:
            return "raise", _raise_to(gs, 0.50)
        return "check", 0

    pot_odds = call_amount / (pot + call_amount)

    if adjusted >= 0.80:
        if _can_raise(gs):
            return "raise", _raise_to(gs, adjusted)
        return "call", 0

    if adjusted >= 0.62:
        if _can_raise(gs) and _rng.random() < 0.60:
            return "raise", _raise_to(gs, adjusted)
        return "call", 0

    if adjusted >= pot_odds + 0.07:
        return "call", 0

    if call_amount <= big_blind and adjusted >= 0.30:
        return "call", 0

    return "fold", 0


def _preflop_strength(hole_cards):
    ranks = sorted((c.rank for c in hole_cards), reverse=True)
    suited = hole_cards[0].suit == hole_cards[1].suit
    gap = ranks[0] - ranks[1]

    if ranks[0] == ranks[1]:
        return min(0.95, 0.50 + ranks[0] / 24)

    strength = ranks[0] / 20 + ranks[1] / 42

    if suited:
        strength += 0.07
    if ranks[1] >= 10:
        strength += 0.10
    elif ranks[1] >= 8:
        strength += 0.04

    if gap == 1:
        strength += 0.05
    elif gap == 2:
        strength += 0.02
    elif gap >= 5:
        strength -= 0.08

    return max(0.05, min(0.92, strength))


# ---------------------------------------------------------------------------
# Postflop (vs other bots)
# ---------------------------------------------------------------------------

def _postflop(gs, opp_count):
    hole = gs["hole_cards"]
    community = gs["community_cards"]
    pot = gs["pot"]
    call_amount = gs["call_amount"]
    stack = gs["stack"]

    equity = _mc_equity(hole, community, opp_count)
    pot_odds = call_amount / (pot + call_amount) if call_amount else 0
    spr = stack / pot if pot > 0 else 10.0

    if call_amount == 0:
        if equity >= 0.58:
            return "raise", _gto_bet(gs, equity, spr)
        if equity >= 0.38 and _has_draw(hole, community) and _rng.random() < 0.32:
            return "raise", _gto_bet(gs, 0.50, spr)
        return "check", 0

    if equity >= pot_odds + 0.14 and equity >= 0.62:
        if _can_raise(gs):
            return "raise", _raise_to(gs, equity)
        return "call", 0

    if equity >= pot_odds + 0.04:
        return "call", 0

    if equity >= 0.38 and _has_draw(hole, community):
        if _can_raise(gs) and _rng.random() < 0.38:
            return "raise", _raise_to(gs, 0.55)
        if equity >= pot_odds - 0.04:
            return "call", 0

    return "fold", 0


def _gto_bet(gs, equity, spr):
    pot = gs["pot"]
    my_bet = gs["my_bet"]
    big_blind = gs["big_blind"]
    stack = gs["stack"]

    if equity >= 0.80:
        fraction = 1.0 if spr < 3 else 0.75
    elif equity >= 0.65:
        fraction = 0.60
    else:
        fraction = 0.45

    additional = max(int(pot * fraction), big_blind)
    target = my_bet + additional
    return min(target, my_bet + stack)


# ---------------------------------------------------------------------------
# Monte Carlo equity
# ---------------------------------------------------------------------------

def _mc_equity(hole_cards, community_cards, opponents, samples=_MC_SAMPLES):
    used = {(c.rank, c.suit) for c in hole_cards + community_cards}
    deck = [Card(r, s) for r, s in _DECK if (r, s) not in used]

    board_needed = 5 - len(community_cards)
    opp_count = min(opponents, 8)
    cards_needed = opp_count * 2 + board_needed

    wins = 0.0

    for _ in range(samples):
        if cards_needed > len(deck):
            break
        sample = _rng.sample(deck, cards_needed)

        idx = 0
        opp_hands = []
        for _ in range(opp_count):
            opp_hands.append([sample[idx], sample[idx + 1]])
            idx += 2
        board = list(community_cards) + sample[idx:]

        if len(board) < 5:
            continue

        my_score = evaluate_hand(hole_cards + board)
        best_opp = max(evaluate_hand(h + board) for h in opp_hands) if opp_hands else (0,)

        if my_score > best_opp:
            wins += 1.0
        elif my_score == best_opp:
            wins += 0.5

    return wins / samples if samples > 0 else 0.5


# ---------------------------------------------------------------------------
# Draw detection
# ---------------------------------------------------------------------------

def _has_draw(hole_cards, community_cards):
    cards = hole_cards + community_cards
    return _flush_draw(cards) or _oesd(cards)


def _flush_draw(cards):
    suits = [c.suit for c in cards]
    return any(suits.count(s) >= 4 for s in suits)


def _oesd(cards):
    ranks = sorted({c.rank for c in cards})
    if 14 in ranks:
        ranks = [1] + ranks
    rank_set = set(ranks)
    for start in range(1, 12):
        window = set(range(start, start + 5))
        if len(window & rank_set) == 4:
            missing = list(window - rank_set)
            if len(missing) == 1 and (missing[0] == start or missing[0] == start + 4):
                return True
    return False


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _can_raise(gs):
    return gs["stack"] > gs["call_amount"]


def _raise_to(gs, strength):
    pot = gs["pot"]
    my_bet = gs["my_bet"]
    big_blind = gs["big_blind"]
    min_raise = gs["min_raise"]
    stack = gs["stack"]

    fraction = 0.50 if strength < 0.70 else (0.75 if strength < 0.85 else 1.00)
    target = max(min_raise, my_bet + max(big_blind, int(pot * fraction)))
    return min(target, my_bet + stack)
