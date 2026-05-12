"""Basic bot: plays any ace."""

BOT_NAME = "Basic Ace"
TIER = "basic"
DESCRIPTION = "Calls with an ace, otherwise stays cheap."


def decide(game_state):
    has_ace = any(card.rank == 14 for card in game_state["hole_cards"])

    if has_ace:
        return "call", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
