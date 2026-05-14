"""Commits decisively when stacks get shallow."""

from bots._strategy import decide_with_profile

BOT_NAME = "Short Stack Ninja"
TIER = "competitive"
DESCRIPTION = "Pushes equity when shallow and still finds semi-bluff spots."


def decide(game_state):
    return decide_with_profile(game_state, "short")
