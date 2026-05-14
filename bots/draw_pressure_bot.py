"""Semi-bluffs strong draws instead of passively chasing."""

from bots._strategy import decide_with_profile

BOT_NAME = "Draw Pressure"
TIER = "competitive"
DESCRIPTION = "Presses flush and straight draws when the price is right."


def decide(game_state):
    return decide_with_profile(game_state, "draw")
