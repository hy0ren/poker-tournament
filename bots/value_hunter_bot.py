"""Value-heavy player that avoids needless spew."""

from bots._strategy import decide_with_profile

BOT_NAME = "Value Hunter"
TIER = "competitive"
DESCRIPTION = "Extracts value with made hands while keeping a few credible bluffs."


def decide(game_state):
    return decide_with_profile(game_state, "value")
