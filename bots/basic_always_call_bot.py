"""Basic bot: checks for free and calls every bet."""

BOT_NAME = "Basic Always Call"
TIER = "basic"
DESCRIPTION = "Checks when free, otherwise calls."


def decide(game_state):
    if game_state["call_amount"] == 0:
        return "check", 0
    return "call", 0
