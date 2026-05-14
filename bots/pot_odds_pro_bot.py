"""Disciplined caller that leans on pot odds."""

from bots._strategy import decide_with_profile

BOT_NAME = "Pot Odds Pro"
TIER = "competitive"
DESCRIPTION = "Calls efficiently, value raises strong hands, and mixes small bluffs."


def decide(game_state):
    return decide_with_profile(game_state, "odds")
