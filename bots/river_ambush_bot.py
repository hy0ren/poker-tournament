"""Patient player that turns up pressure late."""

from bots._strategy import decide_with_profile

BOT_NAME = "River Ambush"
TIER = "competitive"
DESCRIPTION = "Keeps ranges tighter early, then bluffs and value bets rivers."


def decide(game_state):
    return decide_with_profile(game_state, "river")
