"""Advanced bot: bets big with made hands after the flop."""

from poker_tournament.hand_eval import evaluate_hand

BOT_NAME = "Value Bot"
TIER = "advanced"
DESCRIPTION = "Raises made hands, folds weak postflop spots."


def decide(game_state):
    cards = game_state["hole_cards"] + game_state["community_cards"]

    if len(cards) < 5:
        if game_state["call_amount"] == 0:
            return "check", 0
        return "call", 0

    hand_rank = evaluate_hand(cards)[0]
    if hand_rank >= 1 and game_state["stack"] > game_state["call_amount"]:
        target = game_state["my_bet"] + max(game_state["big_blind"], int(game_state["pot"] * 0.8))
        return "raise", max(game_state["min_raise"], target)
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
