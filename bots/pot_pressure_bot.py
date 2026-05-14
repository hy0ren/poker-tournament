"""Sizes bets around the pot to force difficult calls."""

from bots._strategy import decide_with_profile

BOT_NAME = "Pot Pressure"
TIER = "competitive"
DESCRIPTION = "Uses larger pressure bets with value hands and selected bluffs."


def decide(game_state):
    return decide_with_profile(game_state, "pressure")
