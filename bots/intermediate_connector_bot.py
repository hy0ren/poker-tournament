"""Intermediate bot: plays connected cards."""

BOT_NAME = "Connector Bot"
TIER = "intermediate"
DESCRIPTION = "Calls with cards close together in rank."


def decide(game_state):
    ranks = sorted(card.rank for card in game_state["hole_cards"])
    connected = ranks[1] - ranks[0] <= 1

    if connected:
        return "call", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
