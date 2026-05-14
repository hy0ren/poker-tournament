# Poker Bot Tournament

A workshop-friendly Texas Hold'em bot tournament with:

- A 13-bot competitive lineup in `bots/`
- A Python engine with no runtime dependencies
- A FastAPI web demo with a poker-table replay UI
- A simple bot contract: write `decide(game_state)` and return an action
- Run up to 23 bots at one table
- Batch-run tournaments to see which bot wins most often

The app caps each tournament at 23 bots because a standard deck can seat at most 23 Hold'em players while still leaving 5 community cards.

## Quick Start

Run the bundled bots from the command line:

```bash
python run_tournament.py bots/god_bot.py \
  bots/balanced_shark_bot.py \
  bots/all_in_every_hand_bot.py \
  --mode fixed --hands 25 --seed 7
```

Run the browser demo:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run_web.py
```

Open <http://127.0.0.1:8000>.

The browser demo includes replay controls, a speed selector from `0.5x` through `Turbo`, and a batch runner that can run 50 tournaments at once.

## Bot Lineup

The bundled lineup has 13 public bots: Henry's Bot, GodBot, one all-in-every-hand bot, and 10 competent strategy bots that value bet, respect pot odds, and sometimes bluff in reasonable spots.

| File | Bot | Idea |
| --- | --- | --- |
| `bots/god_bot.py` | GodBot | Strong hand strength, draw, and pot odds logic |
| `bots/henrys_bot.py` | Henry's Bot | GTO-inspired play with targeted GodBot exploitation |
| `bots/all_in_every_hand_bot.py` | All-In Every Hand | Shoves whenever it can act |
| `bots/balanced_shark_bot.py` | Balanced Shark | Balanced value betting, pot-odds calls, and measured bluffs |
| `bots/button_pressure_bot.py` | Button Pressure | Applies pressure when fewer opponents remain |
| `bots/draw_pressure_bot.py` | Draw Pressure | Semi-bluffs strong draws at reasonable prices |
| `bots/loose_aggressive_bot.py` | Loose Aggressive | Plays wider ranges with controlled bluff frequency |
| `bots/pot_odds_pro_bot.py` | Pot Odds Pro | Calls efficiently and mixes smaller bluffs |
| `bots/pot_pressure_bot.py` | Pot Pressure | Sizes bets around the pot to force difficult calls |
| `bots/river_ambush_bot.py` | River Ambush | Keeps ranges tighter early, then attacks rivers |
| `bots/short_stack_ninja_bot.py` | Short Stack Ninja | Commits decisively when stacks get shallow |
| `bots/tight_aggressive_bot.py` | Tight Aggressive | Starts selective and bets good hands hard |
| `bots/value_hunter_bot.py` | Value Hunter | Extracts value while keeping a few credible bluffs |

## Writing a Bot

Create a Python file with a `decide(game_state)` function:

```python
BOT_NAME = "My Bot"


def decide(game_state):
    if game_state["call_amount"] == 0:
        return "check", 0
    return "call", 0
```

Valid actions are:

- `("fold", 0)`
- `("check", 0)`
- `("call", 0)`
- `("raise", amount)`

For raises, `amount` means the total chips you want committed on the current betting street. The easiest legal raise is:

```python
return "raise", game_state["min_raise"]
```

Useful `game_state` keys:

| Key | Meaning |
| --- | --- |
| `hole_cards` | Your two private `Card` objects |
| `community_cards` | Shared board cards |
| `pot` | Current pot size |
| `current_bet` | Highest bet on this street |
| `call_amount` | Chips needed to call |
| `min_raise` | Smallest legal raise-to amount |
| `stack` | Your remaining chips |
| `my_bet` | Your current street bet |
| `round` | `preflop`, `flop`, `turn`, or `river` |
| `players` | Public info about the other bots |

Card ranks are `2` through `14`, where `14` is an ace. Suits are `h`, `d`, `c`, and `s`.

## Web API

```text
GET  /api/health
GET  /api/bots
POST /api/tournament
```

Example:

```bash
curl -s http://127.0.0.1:8000/api/tournament \
  -H 'Content-Type: application/json' \
  -d '{
    "bots": ["balanced_shark_bot.py", "pot_pressure_bot.py", "value_hunter_bot.py"],
    "mode": "fixed",
    "starting_chips": 1000,
    "small_blind": 10,
    "big_blind": 20,
    "num_hands": 25,
    "seed": 7
  }'
```

The response includes final standings, hand results, and replay events used by the table UI.

## Project Layout

```text
poker_tournament/
  card.py          cards and deck
  hand_eval.py     best 5-card hand evaluator
  player.py        player state
  game.py          single-table Hold'em engine
  tournament.py    tournament runner
  bot_loader.py    bot file importer
bots/              competitive bot lineup
webapp/            FastAPI app and static UI
tests/             engine and web tests
```

## Tests

```bash
python tests/test_poker.py
pytest -q
```
