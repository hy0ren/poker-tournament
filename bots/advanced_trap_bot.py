"""Advanced bot: slowplays strong hands until the river."""

from poker_tournament.hand_eval import evaluate_hand

BOT_NAME = "Trap Bot"
TIER = "advanced"
DESCRIPTION = "Calls strong hands early, raises them on the river."


def decide(game_state):
    cards = game_state["hole_cards"] + game_state["community_cards"]
    strong = len(cards) >= 5 and evaluate_hand(cards)[0] >= 2

    if strong and game_state["round"] == "river" and game_state["stack"] > game_state["call_amount"]:
        return "raise", max(game_state["min_raise"], game_state["my_bet"] + game_state["pot"])
    if strong:
        return "call", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
