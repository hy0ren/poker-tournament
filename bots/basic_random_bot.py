"""Basic bot: picks a simple action at random."""

import random

BOT_NAME = "Basic Random"
TIER = "basic"
DESCRIPTION = "Randomly checks, calls, folds, or raises."


def decide(game_state):
    if game_state["call_amount"] == 0:
        choices = ["check", "raise"]
    else:
        choices = ["fold", "call"]

    action = random.choice(choices)
    if action == "raise":
        return "raise", game_state["min_raise"]
    return action, 0
