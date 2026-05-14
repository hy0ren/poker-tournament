"""Wide aggressive player with controlled bluff frequency."""

from bots._strategy import decide_with_profile

BOT_NAME = "Loose Aggressive"
TIER = "competitive"
DESCRIPTION = "Plays more hands, applies pressure, and bluffs in reasonable spots."


def decide(game_state):
    return decide_with_profile(game_state, "lag")
