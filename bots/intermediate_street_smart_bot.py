"""Intermediate bot: uses different preflop and postflop rules."""

BOT_NAME = "Street Smart"
TIER = "intermediate"
DESCRIPTION = "Loose preflop, tighter after the flop."


def decide(game_state):
    ranks = [card.rank for card in game_state["hole_cards"]]

    if game_state["round"] == "preflop":
        if max(ranks) >= 10:
            return "call", 0
        if game_state["call_amount"] == 0:
            return "check", 0
        return "fold", 0

    paired_board = any(card.rank in ranks for card in game_state["community_cards"])
    if paired_board:
        return "call", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
