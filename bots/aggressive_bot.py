"""
aggressive_bot.py — Example poker bot that always raises to 3× the current bet.

If it cannot raise (insufficient stack), it calls instead.
"""

BOT_NAME = "AggressiveBot"


def decide(game_state):
    """Always try to raise 3× the current bet."""
    current_bet = game_state['current_bet']
    stack = game_state['stack']
    my_bet = game_state['my_bet']
    big_blind = game_state['big_blind']

    # Target raise: 3× current bet (or 3× big blind if no bet yet)
    target = max(current_bet * 3, big_blind * 3)
    call_amount = game_state['call_amount']

    # Can we afford to raise at all?
    if stack > call_amount and target > current_bet:
        # Cap at our total chips
        raise_to = min(target, stack + my_bet)
        return ('raise', raise_to)

    # Fall back to call/check
    if call_amount == 0:
        return ('check', 0)
    return ('call', 0)
