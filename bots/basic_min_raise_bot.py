"""Basic bot: opens with the smallest legal raise."""

BOT_NAME = "Basic Min Raise"
TIER = "basic"
DESCRIPTION = "Raises only when no call is required."


def decide(game_state):
    if game_state["call_amount"] == 0 and game_state["stack"] > 0:
        return "raise", game_state["min_raise"]
    return "call", 0
