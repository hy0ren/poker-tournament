"""Basic bot: plays suited hole cards."""

BOT_NAME = "Basic Suited"
TIER = "basic"
DESCRIPTION = "Calls with suited cards, folds offsuit bets."


def decide(game_state):
    cards = game_state["hole_cards"]
    suited = cards[0].suit == cards[1].suit

    if suited:
        return "call", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
