"""Advanced bot: calls small bets and avoids large pots."""

BOT_NAME = "Small Ball"
TIER = "advanced"
DESCRIPTION = "Calls small bets, folds to large pressure."


def decide(game_state):
    call_amount = game_state["call_amount"]
    pot = game_state["pot"]
    small_bet = call_amount <= max(game_state["big_blind"], pot * 0.2)

    if call_amount == 0:
        return "check", 0
    if small_bet:
        return "call", 0
    return "fold", 0
