"""Intermediate bot: tries to see cheap flops."""

BOT_NAME = "Cheap Flop"
TIER = "intermediate"
DESCRIPTION = "Calls cheap preflop bets, folds expensive ones."


def decide(game_state):
    cheap = game_state["call_amount"] <= game_state["big_blind"]

    if game_state["round"] == "preflop" and cheap:
        return "call", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
