"""Advanced bot: chases flush and straight draws at the right price."""

BOT_NAME = "Draw Chaser"
TIER = "advanced"
DESCRIPTION = "Calls draws when pot odds are reasonable."


def decide(game_state):
    cards = game_state["hole_cards"] + game_state["community_cards"]
    draw = _has_flush_draw(cards) or _has_straight_draw(cards)
    price = game_state["call_amount"] / (game_state["pot"] + game_state["call_amount"]) if game_state["call_amount"] else 0

    if game_state["call_amount"] == 0:
        return "check", 0
    if draw and price <= 0.30:
        return "call", 0
    return "fold", 0


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
