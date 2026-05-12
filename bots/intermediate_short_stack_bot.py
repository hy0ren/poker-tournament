"""Intermediate bot: changes behavior when short stacked."""

BOT_NAME = "Short Stack"
TIER = "intermediate"
DESCRIPTION = "Folds more often below ten big blinds."


def decide(game_state):
    short = game_state["stack"] < 10 * game_state["big_blind"]

    if short and game_state["call_amount"] > 0:
        return "fold", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "call", 0
