"""Basic bot: likes pocket pairs."""

BOT_NAME = "Basic Pair"
TIER = "basic"
DESCRIPTION = "Calls with a pair, folds weak hands."


def decide(game_state):
    cards = game_state["hole_cards"]
    has_pair = cards[0].rank == cards[1].rank

    if has_pair:
        return "call", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
