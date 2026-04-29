# Poker Tournament

A Python framework for running **Texas Hold'em** tournaments between poker bots.
Write your bot as a single Python file, drop it in, and watch the bots fight it out.

---

## Quick Start

```bash
# Clone the repo
git clone https://github.com/hy0ren/poker-tournament.git
cd poker-tournament

# No external dependencies are required.
# Python 3.8+ is sufficient.

# Run the four bundled example bots:
python run_tournament.py bots/random_bot.py bots/call_bot.py \
                         bots/aggressive_bot.py bots/smart_bot.py

# Or point at the whole bots/ directory:
python run_tournament.py bots/

# Quiet mode (summary only):
python run_tournament.py bots/ --quiet
```

---

## CLI Reference

```
python run_tournament.py [BOT ...] [options]

Positional arguments:
  BOT                  One or more .py bot files, or a directory of bot files.

Options:
  --mode {elimination,fixed}
                       Tournament mode (default: elimination).
                         elimination  Play until one player has all the chips.
                         fixed        Play a fixed number of hands.
  --hands N            Hands to play in "fixed" mode (default: 1000).
  --chips N            Starting chip stack per player (default: 1000).
  --small-blind N      Small blind amount (default: 10).
  --big-blind N        Big blind amount (default: 20).
  --quiet, -q          Suppress hand-by-hand output.
```

---

## Writing a Bot

Create a Python file that defines a `decide(game_state)` function:

```python
# my_bot.py

BOT_NAME = "MyBot"   # Optional display name

def decide(game_state):
    """
    Called once per decision point.  Return (action, amount).

    game_state keys
    ---------------
    hole_cards       list[Card]   Your two private cards.
    community_cards  list[Card]   0–5 shared cards on the board.
    pot              int          Total chips in the pot.
    current_bet      int          Highest bet this street.
    call_amount      int          Chips you must add to call.
    min_raise        int          Minimum legal raise-to total.
    stack            int          Your remaining chips.
    my_bet           int          Chips you have already put in this street.
    round            str          'preflop' | 'flop' | 'turn' | 'river'
    big_blind        int
    small_blind      int
    players          list[dict]   Info about other players:
                                    name, stack, bet, total_bet,
                                    folded, all_in

    Card attributes
    ---------------
    card.rank   int   2–14  (11=J, 12=Q, 13=K, 14=A)
    card.suit   str   'h' | 'd' | 'c' | 's'
    str(card)         e.g. "A♠", "T♥"

    Valid return values
    -------------------
    ('fold',  0)          Fold the hand.
    ('check', 0)          Check (only legal when call_amount == 0).
    ('call',  0)          Call the current bet.
    ('raise', amount)     Raise; `amount` is your total bet this street.
    """
    if game_state['call_amount'] == 0:
        return ('check', 0)
    return ('call', 0)
```

### Rules & contract

* The function **must** return a 2-tuple `(action_str, int_amount)`.
* Invalid or unrecognised actions default to **fold**.
* Exceptions raised inside the bot default to **fold** (the traceback is printed).
* `amount` is ignored for `fold`, `check`, and `call`; it is the *total bet this street* for `raise`.

---

## Bundled Bots

| File | Name | Strategy |
|------|------|----------|
| `bots/random_bot.py` | RandomBot | Uniformly random legal action |
| `bots/call_bot.py` | CallBot | Always calls / checks |
| `bots/aggressive_bot.py` | AggressiveBot | Always raises 3× |
| `bots/smart_bot.py` | SmartBot | Hand-strength heuristics + pot odds |

---

## Project Structure

```
poker-tournament/
├── run_tournament.py          CLI entry point
├── poker_tournament/
│   ├── __init__.py
│   ├── card.py                Card and Deck classes
│   ├── hand_eval.py           5–7 card hand evaluator
│   ├── player.py              Player wrapper
│   ├── game.py                Texas Hold'em engine
│   ├── bot_loader.py          Bot file importer
│   └── tournament.py          Tournament runner
└── bots/
    ├── random_bot.py
    ├── call_bot.py
    ├── aggressive_bot.py
    └── smart_bot.py
```

---

## License

MIT