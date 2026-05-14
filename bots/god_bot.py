"""Solver-style heuristic player using equity, pot odds, and stack pressure."""

import random

from poker_tournament.card import Card
from poker_tournament.hand_eval import evaluate_hand

BOT_NAME = "GodBot"
TIER = "specialist"
DESCRIPTION = "Equity-driven strategy with value bets, bluff mixes, and shove defense."

_MC_SAMPLES = 260
_rng = random.Random()
_DECK = [(rank, suit) for rank in range(2, 15) for suit in ("h", "d", "c", "s")]


def decide(game_state):
    call_amount = game_state["call_amount"]
    pot = max(1, game_state["pot"])
    stack = game_state["stack"]
    street = game_state["round"]
    opponents = _active_opponents(game_state)
    equity = _equity(game_state, opponents)
    draw = _has_draw(game_state)
    pot_odds = call_amount / (pot + call_amount) if call_amount else 0
    spr = stack / pot
    pressure = _pressure(call_amount, stack, pot, game_state["big_blind"])

    if call_amount >= stack * 0.72 and equity < _stackoff_threshold(street, opponents, draw):
        return "fold", 0

    if call_amount == 0:
        return _first_in_action(game_state, equity, draw, opponents, spr)

    if equity >= max(0.73, pot_odds + 0.18):
        if _can_raise(game_state) and _raise_is_profitable(game_state, equity, pressure, made=True):
            return "raise", _bet_to(game_state, equity, spr)
        return "call", 0

    if draw and equity >= pot_odds + 0.03:
        if _can_raise(game_state) and _semi_bluff_spot(game_state, opponents, pressure):
            return "raise", _bet_to(game_state, max(equity, 0.56), spr)
        return "call", 0

    if equity >= pot_odds + _call_cushion(street, opponents, pressure):
        return "call", 0

    if _can_raise(game_state) and _bluff_spot(game_state, equity, draw, opponents, pressure):
        return "raise", _bet_to(game_state, 0.54, spr)

    if call_amount <= game_state["big_blind"] and equity >= 0.34 and pressure < 0.25:
        return "call", 0

    return "fold", 0


def _first_in_action(game_state, equity, draw, opponents, spr):
    open_threshold = 0.47 + max(0, opponents - 2) * 0.03
    if game_state["round"] == "preflop":
        open_threshold += 0.01
    if opponents <= 1:
        open_threshold -= 0.06

    if equity >= open_threshold:
        return "raise", _bet_to(game_state, equity, spr)
    if draw and opponents <= 2 and _rng.random() < 0.42:
        return "raise", _bet_to(game_state, 0.55, spr)
    if _bluff_spot(game_state, equity, draw, opponents, pressure=0):
        return "raise", _bet_to(game_state, 0.50, spr)
    return "check", 0


def _equity(game_state, opponents):
    if game_state["round"] == "preflop":
        return _preflop_equity(game_state["hole_cards"], opponents)
    return _monte_carlo_equity(
        game_state["hole_cards"],
        game_state["community_cards"],
        opponents,
    )


def _preflop_equity(hole_cards, opponents):
    ranks = sorted((card.rank for card in hole_cards), reverse=True)
    suited = hole_cards[0].suit == hole_cards[1].suit
    gap = ranks[0] - ranks[1]

    if ranks[0] == ranks[1]:
        equity = 0.54 + ranks[0] / 24
    else:
        equity = ranks[0] / 23 + ranks[1] / 54
        if ranks[0] == 14:
            equity += 0.06
        if ranks[1] >= 11:
            equity += 0.09
        elif ranks[1] >= 9:
            equity += 0.04
        if suited:
            equity += 0.055
        if gap == 1:
            equity += 0.04
        elif gap == 2:
            equity += 0.02
        elif gap >= 5:
            equity -= 0.075

    equity -= max(0, opponents - 1) * 0.03
    return max(0.06, min(0.95, equity))


def _monte_carlo_equity(hole_cards, community_cards, opponents, samples=_MC_SAMPLES):
    used = {(card.rank, card.suit) for card in hole_cards + community_cards}
    deck = [Card(rank, suit) for rank, suit in _DECK if (rank, suit) not in used]
    board_needed = 5 - len(community_cards)
    opponent_count = min(max(1, opponents), 8)
    cards_needed = opponent_count * 2 + board_needed
    wins = 0.0
    trials = 0

    for _ in range(samples):
        if cards_needed > len(deck):
            break
        sample = _rng.sample(deck, cards_needed)
        cursor = 0
        opponent_hands = []
        for _ in range(opponent_count):
            opponent_hands.append([sample[cursor], sample[cursor + 1]])
            cursor += 2
        board = list(community_cards) + sample[cursor:]
        if len(board) < 5:
            continue

        my_score = evaluate_hand(hole_cards + board)
        best_opponent = max(evaluate_hand(hand + board) for hand in opponent_hands)
        if my_score > best_opponent:
            wins += 1.0
        elif my_score == best_opponent:
            wins += 0.5
        trials += 1

    return wins / trials if trials else 0.5


def _active_opponents(game_state):
    return max(1, sum(1 for player in game_state["players"] if not player["folded"]))


def _pressure(call_amount, stack, pot, big_blind):
    if call_amount <= 0:
        return 0
    stack_pressure = call_amount / max(1, stack)
    pot_pressure = call_amount / max(big_blind, pot)
    return max(stack_pressure, min(1.0, pot_pressure))


def _stackoff_threshold(street, opponents, draw):
    threshold = 0.80 + max(0, opponents - 1) * 0.025
    if street == "river":
        threshold += 0.04
    if draw and street != "river":
        threshold -= 0.05
    return min(0.92, threshold)


def _call_cushion(street, opponents, pressure):
    cushion = 0.06 + max(0, opponents - 1) * 0.03 + pressure * 0.12
    if street == "river":
        cushion += 0.03
    return cushion


def _raise_is_profitable(game_state, equity, pressure, made):
    if game_state["min_raise"] - game_state["my_bet"] > game_state["stack"] * 0.70 and equity < 0.86:
        return False
    if pressure > 0.55 and equity < 0.84:
        return False
    if made:
        return equity >= 0.68
    return equity >= 0.50


def _semi_bluff_spot(game_state, opponents, pressure):
    if game_state["round"] == "river" or opponents > 2 or pressure > 0.48:
        return False
    return _rng.random() < 0.46


def _bluff_spot(game_state, equity, draw, opponents, pressure):
    if opponents > 2 or pressure > 0.35:
        return False
    if game_state["round"] == "preflop":
        return 0.34 <= equity < 0.50 and _rng.random() < 0.10
    if draw:
        return False
    return 0.26 <= equity < 0.45 and game_state["pot"] >= game_state["big_blind"] * 3 and _rng.random() < 0.12


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


def _can_raise(game_state):
    return game_state["stack"] > game_state["call_amount"]


def _bet_to(game_state, equity, spr):
    pot = game_state["pot"]
    my_bet = game_state["my_bet"]
    big_blind = game_state["big_blind"]
    stack = game_state["stack"]
    min_raise = game_state["min_raise"]

    if spr <= 1.5 and equity >= 0.78:
        target = my_bet + stack
    elif equity >= 0.84:
        target = my_bet + max(big_blind * 2, int(pot * 1.10))
    elif equity >= 0.68:
        target = my_bet + max(big_blind, int(pot * 0.78))
    else:
        target = my_bet + max(big_blind, int(pot * 0.45))

    return min(max(target, min_raise), my_bet + stack)
