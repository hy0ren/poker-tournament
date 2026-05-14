"""Core tests for the poker tournament project."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from poker_tournament.bot_loader import load_bot, load_bots_from_directory
from poker_tournament.card import Card, Deck
from poker_tournament.game import PokerGame
from poker_tournament.hand_eval import evaluate_hand, hand_name
from poker_tournament.player import Player
from poker_tournament.tournament import Tournament

BOTS_DIR = os.path.join(os.path.dirname(__file__), "..", "bots")
BOT_FILES = [
    "god_bot.py",
    "all_in_every_hand_bot.py",
    "balanced_shark_bot.py",
    "button_pressure_bot.py",
    "draw_pressure_bot.py",
    "henrys_bot.py",
    "loose_aggressive_bot.py",
    "pot_odds_pro_bot.py",
    "pot_pressure_bot.py",
    "river_ambush_bot.py",
    "short_stack_ninja_bot.py",
    "tight_aggressive_bot.py",
    "value_hunter_bot.py",
]
BOT_NAMES = {
    "All-In Every Hand",
    "Balanced Shark",
    "Button Pressure",
    "Draw Pressure",
    "GodBot",
    "Henry's Bot",
    "Loose Aggressive",
    "Pot Odds Pro",
    "Pot Pressure",
    "River Ambush",
    "Short Stack Ninja",
    "Tight Aggressive",
    "Value Hunter",
}


def c(rank, suit):
    return Card(rank, suit)


def always_call(game_state):
    if game_state["call_amount"] == 0:
        return "check", 0
    return "call", 0


def always_fold(game_state):
    return "fold", 0


def test_card_repr_and_dict():
    ace = Card(14, "s")
    assert repr(ace) == "A♠"
    assert ace.to_dict()["text"] == "A♠"
    assert ace.to_dict()["color"] == "black"


def test_deck_deals_cards():
    deck = Deck()
    hand = deck.deal(2)
    assert len(hand) == 2
    assert len(deck) == 50
    assert isinstance(deck.deal(), Card)


def test_hand_ranks():
    assert hand_name(evaluate_hand([c(2, "h"), c(4, "d"), c(7, "s"), c(9, "c"), c(12, "h")])) == "High Card"
    assert hand_name(evaluate_hand([c(2, "h"), c(2, "d"), c(7, "s"), c(9, "c"), c(12, "h")])) == "One Pair"
    assert hand_name(evaluate_hand([c(2, "h"), c(2, "d"), c(7, "s"), c(7, "c"), c(12, "h")])) == "Two Pair"
    assert hand_name(evaluate_hand([c(2, "h"), c(2, "d"), c(2, "s"), c(9, "c"), c(12, "h")])) == "Three of a Kind"
    assert hand_name(evaluate_hand([c(5, "h"), c(6, "d"), c(7, "s"), c(8, "c"), c(9, "h")])) == "Straight"
    assert hand_name(evaluate_hand([c(2, "h"), c(5, "h"), c(7, "h"), c(9, "h"), c(11, "h")])) == "Flush"
    assert hand_name(evaluate_hand([c(3, "h"), c(3, "d"), c(3, "s"), c(7, "c"), c(7, "h")])) == "Full House"
    assert hand_name(evaluate_hand([c(9, "h"), c(9, "d"), c(9, "s"), c(9, "c"), c(5, "h")])) == "Four of a Kind"
    assert hand_name(evaluate_hand([c(5, "h"), c(6, "h"), c(7, "h"), c(8, "h"), c(9, "h")])) == "Straight Flush"


def test_wheel_straight_and_best_of_seven():
    wheel = evaluate_hand([c(14, "h"), c(2, "d"), c(3, "s"), c(4, "c"), c(5, "h")])
    assert wheel == (4, 5)
    best = evaluate_hand([
        c(9, "h"), c(9, "d"), c(9, "s"), c(9, "c"),
        c(5, "h"), c(2, "d"), c(3, "s"),
    ])
    assert best[0] == 7


def test_game_produces_replay_events_and_conserves_chips():
    players = [
        Player("Alice", 500, always_call),
        Player("Bob", 500, always_call),
    ]
    game = PokerGame(players, verbose=False)
    result = game.play_hand()
    assert result is not None
    assert result["events"]
    assert "snapshot" in result["events"][0]
    assert sum(player.stack for player in players) == 1000


def test_folder_loses_without_breaking_chip_count():
    players = [
        Player("Folder", 500, always_fold),
        Player("Caller", 500, always_call),
    ]
    game = PokerGame(players, verbose=False)
    result = game.play_hand()
    assert result["winners"] == ["Caller"]
    assert sum(player.stack for player in players) == 1000


def test_side_pots():
    game = PokerGame([Player("A", 1, always_call), Player("B", 1, always_call)], verbose=False)

    class FakePlayer:
        def __init__(self, name, total_bet, folded=False):
            self.name = name
            self.total_bet = total_bet
            self.folded = folded

    a = FakePlayer("A", 50)
    b = FakePlayer("B", 100)
    c_folded = FakePlayer("C", 100, folded=True)
    pots = game._calculate_side_pots([a, b, c_folded])
    assert pots[0][0] == 150
    assert {player.name for player in pots[0][1]} == {"A", "B"}
    assert pots[1][0] == 100
    assert {player.name for player in pots[1][1]} == {"B"}


def test_load_bundled_bots_and_interface():
    bots = load_bots_from_directory(BOTS_DIR)
    names = {name for name, _ in bots}
    assert names == BOT_NAMES
    assert len(bots) == 13

    state = {
        "hole_cards": [Card(14, "h"), Card(13, "s")],
        "community_cards": [],
        "pot": 30,
        "current_bet": 20,
        "call_amount": 10,
        "min_raise": 40,
        "stack": 990,
        "my_bet": 10,
        "round": "preflop",
        "players": [],
        "big_blind": 20,
        "small_blind": 10,
    }
    valid = {"fold", "check", "call", "raise"}
    for name, decide in bots:
        action, amount = decide(state)
        assert action in valid, name
        assert isinstance(amount, int), name


def test_load_single_bot():
    name, decide = load_bot(os.path.join(BOTS_DIR, "balanced_shark_bot.py"))
    assert name == "Balanced Shark"
    assert callable(decide)


def test_fixed_tournament_payload():
    bots = load_bots_from_directory(BOTS_DIR)
    tournament = Tournament(bots, starting_chips=500, mode="fixed", num_hands=5, verbose=False, seed=3)
    standings = tournament.run()
    payload = tournament.to_payload()
    assert len(standings) == 13
    assert 1 <= payload["hands_played"] <= 5
    assert payload["events"]
    assert sum(row["chips"] for row in standings) == 500 * 13


def test_elimination_tournament_has_safety_cap():
    bots = load_bots_from_directory(BOTS_DIR)
    tournament = Tournament(bots, starting_chips=300, mode="elimination", num_hands=50, verbose=False, seed=9)
    standings = tournament.run()
    assert standings[0]["rank"] == 1
    assert standings[0]["chips"] > 0
    assert len(tournament.hands) <= 50


def test_tournament_rejects_more_than_23_bots():
    _, decide = load_bot(os.path.join(BOTS_DIR, "balanced_shark_bot.py"))
    bots = [(f"Bot {index + 1}", decide) for index in range(24)]
    try:
        Tournament(bots, starting_chips=200, mode="fixed", num_hands=2, verbose=False, seed=4)
    except ValueError as exc:
        assert "at most 23" in str(exc)
    else:
        raise AssertionError("Expected Tournament to reject more than 23 bots")
