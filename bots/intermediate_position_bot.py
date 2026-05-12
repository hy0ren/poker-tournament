"""Intermediate bot: reacts to active opponents."""

BOT_NAME = "Position Bot"
TIER = "intermediate"
DESCRIPTION = "Raises when few opponents remain."


def decide(game_state):
    active_opponents = 0
    for player in game_state["players"]:
        if not player["folded"]:
            active_opponents += 1

    if active_opponents <= 2 and game_state["my_bet"] == 0:
        return "raise", game_state["min_raise"]
    if game_state["call_amount"] == 0:
        return "check", 0
    return "call", 0
