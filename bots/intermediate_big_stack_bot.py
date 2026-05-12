"""Intermediate bot: uses stack size for aggression."""

BOT_NAME = "Big Stack"
TIER = "intermediate"
DESCRIPTION = "Raises when deep stacked, otherwise calls."


def decide(game_state):
    deep_stack = game_state["stack"] >= 20 * game_state["big_blind"]

    if deep_stack and game_state["my_bet"] == 0 and game_state["stack"] > game_state["call_amount"]:
        return "raise", game_state["min_raise"]
    if game_state["call_amount"] == 0:
        return "check", 0
    return "call", 0
