"""Tight preflop ranges with aggressive value betting."""

from bots._strategy import decide_with_profile

BOT_NAME = "Tight Aggressive"
TIER = "competitive"
DESCRIPTION = "Starts selective, bets good hands hard, and bluffs sparingly."


def decide(game_state):
    return decide_with_profile(game_state, "tag")
