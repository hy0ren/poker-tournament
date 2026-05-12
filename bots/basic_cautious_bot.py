"""Basic bot: avoids paying for hands."""

BOT_NAME = "Basic Cautious"
TIER = "basic"
DESCRIPTION = "Checks when free, folds to any bet."


def decide(game_state):
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
