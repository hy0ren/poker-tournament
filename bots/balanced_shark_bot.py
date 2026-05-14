"""Solid balanced player with selective pressure."""

from bots._strategy import decide_with_profile

BOT_NAME = "Balanced Shark"
TIER = "competitive"
DESCRIPTION = "Balanced value betting, pot-odds calls, and measured bluffs."


def decide(game_state):
    return decide_with_profile(game_state, "balanced")
