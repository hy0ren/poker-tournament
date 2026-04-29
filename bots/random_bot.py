"""
random_bot.py — Example poker bot that picks a random legal action.

The decide() function must accept a game_state dict and return
(action, amount).  See the README for the full game_state schema.
"""

import random

BOT_NAME = "RandomBot"


def decide(game_state):
    """Choose a uniformly random legal action."""
    call_amount = game_state['call_amount']
    stack = game_state['stack']

    choices = ['fold', 'call']

    # Can raise if we have chips beyond the call
    if stack > call_amount:
        choices.append('raise')

    # Can check instead of call when call_amount is 0
    if call_amount == 0:
        choices = ['check', 'raise'] if stack > 0 else ['check']

    action = random.choice(choices)

    if action == 'raise':
        min_raise = game_state['min_raise']
        max_raise = game_state['stack'] + game_state['my_bet']
        amount = random.randint(min_raise, max(min_raise, max_raise))
        return ('raise', amount)

    return (action, 0)
