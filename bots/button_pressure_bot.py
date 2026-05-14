"""Attacks more often when fewer opponents remain."""

from bots._strategy import decide_with_profile

BOT_NAME = "Button Pressure"
TIER = "competitive"
DESCRIPTION = "Uses position-like pressure and occasional heads-up bluffs."


def decide(game_state):
    return decide_with_profile(game_state, "position")
