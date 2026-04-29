"""
call_bot.py — Example poker bot that always calls (or checks).

Never raises, never folds.
"""

BOT_NAME = "CallBot"


def decide(game_state):
    """Always call (or check when there is no bet)."""
    if game_state['call_amount'] == 0:
        return ('check', 0)
    return ('call', 0)
