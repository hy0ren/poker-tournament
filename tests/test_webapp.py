"""Tests for the web API and static UI."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient  # noqa: E402

from webapp.server import app  # noqa: E402

BOT_FILES = [
    "advanced_draw_chaser_bot.py",
    "advanced_god_bot.py",
    "advanced_maniac_bot.py",
    "advanced_pot_pressure_bot.py",
    "advanced_small_ball_bot.py",
    "advanced_three_bet_bot.py",
    "advanced_trap_bot.py",
    "advanced_value_bot.py",
    "basic_ace_bot.py",
    "basic_always_call_bot.py",
    "basic_cautious_bot.py",
    "basic_face_card_bot.py",
    "basic_min_raise_bot.py",
    "basic_pair_bot.py",
    "basic_random_bot.py",
    "basic_suited_bot.py",
    "intermediate_big_stack_bot.py",
    "intermediate_cheap_flop_bot.py",
    "intermediate_connector_bot.py",
    "intermediate_position_bot.py",
    "intermediate_pot_odds_bot.py",
    "intermediate_short_stack_bot.py",
    "intermediate_street_smart_bot.py",
    "intermediate_top_pair_bot.py",
]
BOT_NAMES = {
    "Basic Ace",
    "Basic Always Call",
    "Basic Cautious",
    "Basic Face Card",
    "Basic Min Raise",
    "Basic Pair",
    "Basic Random",
    "Basic Suited",
    "Big Stack",
    "Cheap Flop",
    "Connector Bot",
    "Draw Chaser",
    "GodBot",
    "Maniac Bot",
    "Position Bot",
    "Pot Odds",
    "Pot Pressure",
    "Short Stack",
    "Small Ball",
    "Street Smart",
    "Three Bet Bot",
    "Top Pair",
    "Trap Bot",
    "Value Bot",
}


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_list_bots_includes_source(client):
    response = client.get("/api/bots")
    assert response.status_code == 200
    bots = response.json()["bots"]
    names = {bot["name"] for bot in bots}
    assert names == BOT_NAMES
    assert len(bots) == 24
    tiers = {}
    for bot in bots:
        tiers[bot["tier"]] = tiers.get(bot["tier"], 0) + 1
    assert tiers == {"basic": 8, "intermediate": 8, "advanced": 8}
    assert all("def decide" in bot["source"] for bot in bots)


def test_run_tournament_returns_replay_data(client):
    response = client.post(
        "/api/tournament",
        json={
            "bots": ["basic_always_call_bot.py", "basic_min_raise_bot.py", "basic_ace_bot.py"],
            "mode": "fixed",
            "starting_chips": 500,
            "small_blind": 10,
            "big_blind": 20,
            "num_hands": 5,
            "seed": 11,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["hands_played"] == 5
    assert len(data["standings"]) == 3
    assert data["hands"]
    assert data["events"]
    assert "snapshot" in data["events"][0]
    assert sum(row["chips"] for row in data["standings"]) == 1500


def test_run_tournament_rejects_more_than_23_bots(client):
    response = client.post(
        "/api/tournament",
        json={
            "bots": BOT_FILES,
            "mode": "fixed",
            "starting_chips": 100,
            "small_blind": 1,
            "big_blind": 2,
            "num_hands": 2,
            "seed": 2,
        },
    )
    assert response.status_code == 422


def test_run_batch_returns_frequent_winners(client):
    response = client.post(
        "/api/batch",
        json={
            "bots": [
                "basic_always_call_bot.py",
                "basic_min_raise_bot.py",
                "basic_ace_bot.py",
            ],
            "mode": "fixed",
            "starting_chips": 500,
            "small_blind": 10,
            "big_blind": 20,
            "num_hands": 5,
            "runs": 50,
            "seed": 5,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["runs"] == 50
    assert len(data["results"]) == 3
    assert sum(row["wins"] for row in data["results"]) == 50
    assert data["results"][0]["wins"] >= data["results"][-1]["wins"]


def test_validation_errors(client):
    response = client.post(
        "/api/tournament",
        json={
            "bots": ["basic_always_call_bot.py"],
            "mode": "fixed",
            "starting_chips": 500,
            "small_blind": 10,
            "big_blind": 20,
            "num_hands": 5,
        },
    )
    assert response.status_code == 422

    response = client.post(
        "/api/tournament",
        json={
            "bots": ["basic_always_call_bot.py", "../bad.py"],
            "mode": "fixed",
            "starting_chips": 500,
            "small_blind": 10,
            "big_blind": 20,
            "num_hands": 5,
        },
    )
    assert response.status_code == 422

    response = client.post(
        "/api/tournament",
        json={
            "bots": ["basic_always_call_bot.py", "basic_random_bot.py"],
            "mode": "fixed",
            "starting_chips": 500,
            "small_blind": 20,
            "big_blind": 20,
            "num_hands": 5,
        },
    )
    assert response.status_code == 400


def test_unknown_bot(client):
    response = client.post(
        "/api/tournament",
        json={
            "bots": ["basic_always_call_bot.py", "missing.py"],
            "mode": "fixed",
            "starting_chips": 500,
            "small_blind": 10,
            "big_blind": 20,
            "num_hands": 5,
        },
    )
    assert response.status_code == 400
    assert "missing.py" in response.json()["detail"]


def test_static_ui_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Poker Bot Tournament" in response.text
    assert "poker-table" in response.text
    assert "replay-speed" in response.text
    assert "batch-runs" in response.text

    for path in ("/assets/styles.css", "/assets/app.js"):
        response = client.get(path)
        assert response.status_code == 200
