"""Basic bot: plays hands with a queen or better."""

BOT_NAME = "Basic Face Card"
TIER = "basic"
DESCRIPTION = "Calls with a queen, king, or ace."


def decide(game_state):
    high_card = max(card.rank for card in game_state["hole_cards"])

    if high_card >= 12:
        return "call", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
