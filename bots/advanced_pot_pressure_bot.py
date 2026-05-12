"""Advanced bot: sizes raises as a fraction of the pot."""

BOT_NAME = "Pot Pressure"
TIER = "advanced"
DESCRIPTION = "Raises to pressure the pot with strong cards."


def decide(game_state):
    ranks = [card.rank for card in game_state["hole_cards"]]
    strong = max(ranks) >= 13 or ranks[0] == ranks[1]

    if strong and game_state["my_bet"] == 0 and game_state["stack"] > game_state["call_amount"]:
        target = game_state["my_bet"] + max(game_state["big_blind"], int(game_state["pot"] * 0.75))
        return "raise", max(game_state["min_raise"], target)
    if game_state["call_amount"] <= game_state["pot"] / 5:
        return "call", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
