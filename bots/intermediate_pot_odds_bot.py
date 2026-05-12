"""Intermediate bot: compares call price to pot size."""

BOT_NAME = "Pot Odds"
TIER = "intermediate"
DESCRIPTION = "Calls when the price is less than a quarter of the pot."


def decide(game_state):
    call_amount = game_state["call_amount"]
    pot = game_state["pot"]

    if call_amount == 0:
        return "check", 0
    if call_amount <= pot / 4:
        return "call", 0
    return "fold", 0
