"""Shoves every hand, every street."""

BOT_NAME = "All-In Every Hand"
TIER = "specialist"
DESCRIPTION = "Moves all-in whenever it can act."


def decide(game_state):
    if game_state["stack"] <= game_state["call_amount"]:
        return "call", 0
    return "raise", game_state["my_bet"] + game_state["stack"]
