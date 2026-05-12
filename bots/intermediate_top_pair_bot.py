"""Intermediate bot: looks for top pair after the flop."""

BOT_NAME = "Top Pair"
TIER = "intermediate"
DESCRIPTION = "Raises when a hole card pairs the board high card."


def decide(game_state):
    board = game_state["community_cards"]
    if not board:
        if game_state["call_amount"] == 0:
            return "check", 0
        return "call", 0

    top_board_rank = max(card.rank for card in board)
    has_top_pair = any(card.rank == top_board_rank for card in game_state["hole_cards"])

    if has_top_pair and game_state["my_bet"] == 0:
        return "raise", game_state["min_raise"]
    if has_top_pair:
        return "call", 0
    if game_state["call_amount"] == 0:
        return "check", 0
    return "fold", 0
