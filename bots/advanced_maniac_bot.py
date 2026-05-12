"""Advanced bot: applies constant betting pressure."""

BOT_NAME = "Maniac Bot"
TIER = "advanced"
DESCRIPTION = "Raises and re-raises with a wide range."


def decide(game_state):
    affordable = game_state["stack"] > game_state["call_amount"]
    raise_to = max(game_state["min_raise"], game_state["current_bet"] + 2 * game_state["big_blind"])

    if affordable:
        return "raise", raise_to
    if game_state["call_amount"] == 0:
        return "check", 0
    return "call", 0
