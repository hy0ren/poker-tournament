"""Advanced bot: re-raises strong preflop hands."""

BOT_NAME = "Three Bet Bot"
TIER = "advanced"
DESCRIPTION = "3-bets premium hands and folds weak hands to raises."


def decide(game_state):
    ranks = sorted((card.rank for card in game_state["hole_cards"]), reverse=True)
    pair = ranks[0] == ranks[1]
    premium = pair and ranks[0] >= 10 or ranks == [14, 13] or ranks == [14, 12]
    facing_raise = game_state["call_amount"] > game_state["big_blind"]

    if premium and game_state["stack"] > game_state["call_amount"]:
        return "raise", max(game_state["min_raise"], game_state["current_bet"] + 3 * game_state["big_blind"])
    if facing_raise and not premium:
        return "fold", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "call", 0
