"""Shared decision helpers for the competitive bot roster."""

import random

from poker_tournament.hand_eval import evaluate_hand

_rng = random.Random()


PROFILES = {
    "balanced": {
        "open": 0.54,
        "value": 0.62,
        "call_pad": 0.08,
        "bluff": 0.13,
        "semi_bluff": 0.34,
        "aggression": 0.58,
        "looseness": 0.00,
    },
    "position": {
        "open": 0.50,
        "value": 0.60,
        "call_pad": 0.06,
        "bluff": 0.16,
        "semi_bluff": 0.38,
        "aggression": 0.62,
        "looseness": 0.03,
    },
    "pressure": {
        "open": 0.48,
        "value": 0.58,
        "call_pad": 0.04,
        "bluff": 0.19,
        "semi_bluff": 0.42,
        "aggression": 0.78,
        "looseness": 0.05,
    },
    "value": {
        "open": 0.58,
        "value": 0.66,
        "call_pad": 0.10,
        "bluff": 0.08,
        "semi_bluff": 0.26,
        "aggression": 0.70,
        "looseness": -0.02,
    },
    "draw": {
        "open": 0.52,
        "value": 0.61,
        "call_pad": 0.05,
        "bluff": 0.11,
        "semi_bluff": 0.52,
        "aggression": 0.66,
        "looseness": 0.03,
    },
    "tag": {
        "open": 0.60,
        "value": 0.65,
        "call_pad": 0.09,
        "bluff": 0.10,
        "semi_bluff": 0.31,
        "aggression": 0.64,
        "looseness": -0.04,
    },
    "lag": {
        "open": 0.46,
        "value": 0.57,
        "call_pad": 0.03,
        "bluff": 0.21,
        "semi_bluff": 0.45,
        "aggression": 0.74,
        "looseness": 0.07,
    },
    "odds": {
        "open": 0.55,
        "value": 0.63,
        "call_pad": 0.13,
        "bluff": 0.09,
        "semi_bluff": 0.30,
        "aggression": 0.54,
        "looseness": 0.01,
    },
    "short": {
        "open": 0.56,
        "value": 0.60,
        "call_pad": 0.06,
        "bluff": 0.14,
        "semi_bluff": 0.34,
        "aggression": 0.86,
        "looseness": 0.01,
    },
    "river": {
        "open": 0.57,
        "value": 0.68,
        "call_pad": 0.08,
        "bluff": 0.12,
        "semi_bluff": 0.28,
        "aggression": 0.60,
        "looseness": -0.01,
    },
}


def decide_with_profile(game_state, profile_name):
    profile = PROFILES[profile_name]
    strength = _estimate_strength(game_state)
    call_amount = game_state["call_amount"]
    pot = max(1, game_state["pot"])
    big_blind = game_state["big_blind"]
    active_opponents = sum(1 for player in game_state["players"] if not player["folded"])
    heads_up_bonus = 0.06 if active_opponents <= 1 else 0
    multiway_tax = max(0, active_opponents - 2) * 0.025
    adjusted = strength + profile["looseness"] + heads_up_bonus - multiway_tax
    draw = _has_draw(game_state)
    pot_odds = call_amount / (pot + call_amount) if call_amount else 0

    if call_amount >= game_state["stack"] * 0.75 and adjusted < 0.84:
        return "fold", 0

    if profile_name == "short" and _stack_to_pot_ratio(game_state) < 3.0:
        adjusted += 0.07
    if profile_name == "position" and active_opponents <= 2:
        adjusted += 0.05
    if profile_name == "river" and game_state["round"] == "river":
        adjusted += 0.05

    if call_amount == 0:
        if adjusted >= profile["open"]:
            return "raise", _bet_to(game_state, adjusted, profile)
        if draw and _rng.random() < profile["semi_bluff"]:
            return "raise", _bet_to(game_state, 0.52, profile)
        if _good_bluff_spot(game_state, adjusted, active_opponents) and _rng.random() < profile["bluff"]:
            return "raise", _bet_to(game_state, 0.48, profile)
        return "check", 0

    if adjusted >= max(profile["value"], pot_odds + profile["call_pad"] + 0.12):
        if _can_raise(game_state) and _raise_is_reasonable(game_state, adjusted) and _rng.random() < profile["aggression"]:
            return "raise", _bet_to(game_state, adjusted, profile)
        return "call", 0

    if draw and adjusted >= pot_odds - 0.03:
        if _can_raise(game_state) and _raise_is_reasonable(game_state, adjusted) and _rng.random() < profile["semi_bluff"]:
            return "raise", _bet_to(game_state, 0.54, profile)
        return "call", 0

    if adjusted >= pot_odds + profile["call_pad"]:
        return "call", 0

    if call_amount <= big_blind and adjusted >= 0.30:
        return "call", 0

    if _can_raise(game_state) and _good_bluff_spot(game_state, adjusted, active_opponents):
        pressure_is_reasonable = call_amount <= max(big_blind * 3, int(pot * 0.45))
        if pressure_is_reasonable and _rng.random() < profile["bluff"] * 0.55:
            return "raise", _bet_to(game_state, 0.50, profile)

    return "fold", 0


def _estimate_strength(game_state):
    cards = game_state["hole_cards"] + game_state["community_cards"]
    if len(cards) < 5:
        return _preflop_strength(game_state["hole_cards"])

    score = evaluate_hand(cards)
    made = {
        8: 0.99,
        7: 0.96,
        6: 0.91,
        5: 0.85,
        4: 0.78,
        3: 0.68,
        2: 0.55,
        1: 0.39,
        0: 0.14 + score[1] / 120,
    }[score[0]]
    if _has_draw(game_state):
        made += 0.07
    return min(0.99, made)


def _preflop_strength(hole_cards):
    ranks = sorted((card.rank for card in hole_cards), reverse=True)
    suited = hole_cards[0].suit == hole_cards[1].suit
    gap = ranks[0] - ranks[1]

    if ranks[0] == ranks[1]:
        return min(0.96, 0.48 + ranks[0] / 24)

    strength = ranks[0] / 22 + ranks[1] / 48
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


def _has_draw(game_state):
    cards = game_state["hole_cards"] + game_state["community_cards"]
    return _has_flush_draw(cards) or _has_straight_draw(cards)


def _has_flush_draw(cards):
    suits = [card.suit for card in cards]
    return any(suits.count(suit) >= 4 for suit in set(suits))


def _has_straight_draw(cards):
    ranks = {card.rank for card in cards}
    if 14 in ranks:
        ranks.add(1)
    for start in range(1, 11):
        if len(set(range(start, start + 5)) & ranks) >= 4:
            return True
    return False


def _good_bluff_spot(game_state, adjusted_strength, active_opponents):
    if active_opponents > 2:
        return False
    if game_state["round"] == "preflop" and adjusted_strength < 0.34:
        return False
    if game_state["round"] != "preflop" and adjusted_strength < 0.28:
        return False
    return game_state["pot"] >= game_state["big_blind"] * 2


def _stack_to_pot_ratio(game_state):
    return game_state["stack"] / max(1, game_state["pot"])


def _can_raise(game_state):
    return game_state["stack"] > game_state["call_amount"]


def _raise_is_reasonable(game_state, strength):
    extra_for_min_raise = game_state["min_raise"] - game_state["my_bet"]
    if extra_for_min_raise > game_state["stack"] * 0.65 and strength < 0.86:
        return False
    if game_state["current_bet"] > game_state["big_blind"] * 5 and strength < 0.86:
        return False
    if game_state["my_bet"] > game_state["big_blind"] * 4 and strength < 0.86:
        return False
    if game_state["call_amount"] > max(game_state["big_blind"] * 4, int(game_state["pot"] * 0.40)):
        return strength >= 0.82
    return True


def _bet_to(game_state, strength, profile):
    pot = game_state["pot"]
    my_bet = game_state["my_bet"]
    big_blind = game_state["big_blind"]
    stack = game_state["stack"]
    min_raise = game_state["min_raise"]

    if strength >= 0.78:
        fraction = 0.82
    elif strength >= 0.62:
        fraction = 0.62
    else:
        fraction = 0.44
    fraction *= 0.85 + profile["aggression"] * 0.35

    target = max(min_raise, my_bet + max(big_blind, int(pot * fraction)))
    return min(target, my_bet + stack)
