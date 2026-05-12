# Poker Bot Tournament

A workshop-friendly Texas Hold'em bot tournament with:

- Tiny example bots in `bots/`
- A Python engine with no runtime dependencies
- A FastAPI web demo with a poker-table replay UI
- A simple bot contract: write `decide(game_state)` and return an action
- Run up to 23 bots at one table
- Batch-run tournaments to see which bot wins most often

The app caps each tournament at 23 bots because a standard deck can seat at most 23 Hold'em players while still leaving 5 community cards.

## Quick Start

Run the bundled bots from the command line:

```bash
python run_tournament.py bots/basic_always_call_bot.py \
  bots/basic_min_raise_bot.py \
  bots/advanced_god_bot.py \
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

## Example Bots

The bundled bots are grouped into 8 basic, 8 intermediate, and 8 advanced examples:

| File | Bot | Idea |
| --- | --- | --- |
| `bots/basic_always_call_bot.py` | Basic Always Call | Check for free, otherwise call |
| `bots/basic_cautious_bot.py` | Basic Cautious | Check for free, fold to bets |
| `bots/basic_min_raise_bot.py` | Basic Min Raise | Open with the minimum raise |
| `bots/basic_random_bot.py` | Basic Random | Pick a simple legal action at random |
| `bots/basic_ace_bot.py` | Basic Ace | Continue with any ace |
| `bots/basic_pair_bot.py` | Basic Pair | Continue with pocket pairs |
| `bots/basic_suited_bot.py` | Basic Suited | Continue with suited cards |
| `bots/basic_face_card_bot.py` | Basic Face Card | Continue with queen or better |
| `bots/intermediate_cheap_flop_bot.py` | Cheap Flop | See cheap flops, fold expensive ones |
| `bots/intermediate_connector_bot.py` | Connector Bot | Continue with connected cards |
| `bots/intermediate_short_stack_bot.py` | Short Stack | Protect a small stack |
| `bots/intermediate_big_stack_bot.py` | Big Stack | Raise when deep stacked |
| `bots/intermediate_pot_odds_bot.py` | Pot Odds | Call when the price is small vs the pot |
| `bots/intermediate_position_bot.py` | Position Bot | Raise when few opponents remain |
| `bots/intermediate_top_pair_bot.py` | Top Pair | Raise when pairing the board high card |
| `bots/intermediate_street_smart_bot.py` | Street Smart | Use different preflop/postflop rules |
| `bots/advanced_three_bet_bot.py` | Three Bet Bot | Re-raise premium preflop hands |
| `bots/advanced_pot_pressure_bot.py` | Pot Pressure | Size raises from pot size |
| `bots/advanced_small_ball_bot.py` | Small Ball | Call small bets, avoid large pressure |
| `bots/advanced_maniac_bot.py` | Maniac Bot | Raise and re-raise wide |
| `bots/advanced_value_bot.py` | Value Bot | Bet big with made hands |
| `bots/advanced_trap_bot.py` | Trap Bot | Slowplay then raise river |
| `bots/advanced_draw_chaser_bot.py` | Draw Chaser | Chase draws at the right price |
| `bots/advanced_god_bot.py` | GodBot | Advanced hand strength, draw, and pot odds logic |

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
    "bots": ["basic_always_call_bot.py", "basic_min_raise_bot.py", "basic_ace_bot.py"],
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
bots/              workshop bot examples
webapp/            FastAPI app and static UI
tests/             engine and web tests
```

## Tests

```bash
python tests/test_poker.py
pytest -q
```
