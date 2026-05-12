"""Advanced bot: strong heuristic play using all available public info."""

from poker_tournament.hand_eval import evaluate_hand

BOT_NAME = "GodBot"
TIER = "advanced"
DESCRIPTION = "Advanced hand strength, draw, and pot odds logic."


def decide(game_state):
    strength = _estimate_strength(game_state)
    call_amount = game_state["call_amount"]
    pot = game_state["pot"]
    pot_odds = call_amount / (pot + call_amount) if call_amount else 0

    if call_amount == 0:
        if strength >= 0.55 and _can_raise(game_state):
            return "raise", _raise_amount(game_state, strength)
        return "check", 0

    if strength >= 0.78:
        if _can_raise(game_state):
            return "raise", _raise_amount(game_state, strength)
        return "call", 0

    if strength >= pot_odds + 0.12:
        return "call", 0
    if call_amount <= game_state["big_blind"] and strength >= 0.35:
        return "call", 0
    return "fold", 0


def _estimate_strength(game_state):
    cards = game_state["hole_cards"] + game_state["community_cards"]
    if len(cards) < 5:
        return _preflop_strength(game_state["hole_cards"])

    score = evaluate_hand(cards)
    made_hand = {
        8: 0.99,
        7: 0.96,
        6: 0.92,
        5: 0.86,
        4: 0.80,
        3: 0.70,
        2: 0.58,
        1: 0.42,
        0: 0.16 + score[1] / 100,
    }[score[0]]

    draw_bonus = 0
    if _has_flush_draw(cards):
        draw_bonus += 0.08
    if _has_straight_draw(cards):
        draw_bonus += 0.06
    return min(0.99, made_hand + draw_bonus)


def _preflop_strength(hole_cards):
    ranks = sorted((card.rank for card in hole_cards), reverse=True)
    suited = hole_cards[0].suit == hole_cards[1].suit
    gap = ranks[0] - ranks[1]

    if ranks[0] == ranks[1]:
        return min(0.95, 0.45 + ranks[0] / 25)

    strength = ranks[0] / 20
    if ranks[1] >= 10:
        strength += 0.15
    if suited:
        strength += 0.08
    if gap == 1:
        strength += 0.06
    elif gap >= 4:
        strength -= 0.10
    return max(0.05, min(0.90, strength))


def _has_flush_draw(cards):
    suits = [card.suit for card in cards]
    return any(suits.count(suit) >= 4 for suit in suits)


def _has_straight_draw(cards):
    ranks = {card.rank for card in cards}
    if 14 in ranks:
        ranks.add(1)
    for start in range(1, 11):
        if len(set(range(start, start + 5)) & ranks) >= 4:
            return True
    return False


def _can_raise(game_state):
    return game_state["my_bet"] == 0 and game_state["stack"] > game_state["call_amount"]


def _raise_amount(game_state, strength):
    pressure = 0.5 if strength < 0.78 else 0.85
    target = game_state["my_bet"] + max(game_state["big_blind"], int(game_state["pot"] * pressure))
    return min(max(target, game_state["min_raise"]), game_state["my_bet"] + game_state["stack"])
