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
    assert len(bots) == 13
    assert all("def decide" in bot["source"] for bot in bots)


def test_run_tournament_returns_replay_data(client):
    response = client.post(
        "/api/tournament",
        json={
            "bots": ["balanced_shark_bot.py", "pot_pressure_bot.py", "value_hunter_bot.py"],
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
    assert 1 <= data["hands_played"] <= 5
    assert len(data["standings"]) == 3
    assert data["hands"]
    assert data["events"]
    assert "snapshot" in data["events"][0]
    assert sum(row["chips"] for row in data["standings"]) == 1500


def test_run_tournament_rejects_more_than_23_bots(client):
    response = client.post(
        "/api/tournament",
        json={
            "bots": BOT_FILES + BOT_FILES,
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
                "balanced_shark_bot.py",
                "pot_pressure_bot.py",
                "value_hunter_bot.py",
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


def test_play_session_waits_for_human_action(client):
    response = client.post(
        "/api/play/start",
        json={
            "bots": ["balanced_shark_bot.py", "value_hunter_bot.py"],
            "starting_chips": 1000,
            "small_blind": 10,
            "big_blind": 20,
            "num_hands": 3,
            "seed": 12,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["pending"]["player"] == "You"
    assert data["snapshot"]["street"] == "preflop"
    assert "fold" in data["pending"]["legal_actions"]
    players = data["pending"]["snapshot"]["players"]
    assert len(players[0]["cards"]) == 2
    assert all(not player["cards"] for player in players[1:])

    action = "check" if "check" in data["pending"]["legal_actions"] else "fold"
    response = client.post(
        f"/api/play/{data['session_id']}/act",
        json={"action": action, "amount": 0},
    )
    assert response.status_code == 200, response.text
    next_data = response.json()
    assert next_data["session_id"] == data["session_id"]
    assert next_data["events"]
    assert next_data["snapshot"]["community_cards"] == next_data["events"][-1]["snapshot"]["community_cards"]


def test_play_session_reveals_all_cards_when_hand_ends(client):
    response = client.post(
        "/api/play/start",
        json={
            "bots": ["balanced_shark_bot.py"],
            "starting_chips": 1000,
            "small_blind": 10,
            "big_blind": 20,
            "num_hands": 1,
            "seed": 12,
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    response = client.post(
        f"/api/play/{data['session_id']}/act",
        json={"action": "fold", "amount": 0},
    )
    assert response.status_code == 200, response.text
    finished = response.json()
    assert finished["events"][-1]["type"] in {"reveal", "play_complete"}
    assert finished["snapshot"]["street"] == "showdown"
    assert all(len(player["cards"]) == 2 for player in finished["snapshot"]["players"])


def test_validation_errors(client):
    response = client.post(
        "/api/tournament",
        json={
            "bots": ["balanced_shark_bot.py"],
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
            "bots": ["balanced_shark_bot.py", "../bad.py"],
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
            "bots": ["balanced_shark_bot.py", "pot_pressure_bot.py"],
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
            "bots": ["balanced_shark_bot.py", "missing.py"],
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
    assert "play-panel" in response.text
    assert "all-in-btn" in response.text
    assert "replay-speed" in response.text
    assert "batch-runs" in response.text

    for path in ("/assets/styles.css", "/assets/app.js"):
        response = client.get(path)
        assert response.status_code == 200

    response = client.get("/assets/app.js")
    assert "seat-state" in response.text
    assert "is-back" in response.text
    assert "submitAllInAction" in response.text
    assert "REVEAL_EVENT_DELAY_MS" in response.text
    assert "humanIsStillIn" in response.text
    assert "scaledPlayDelay" in response.text
    assert "foldedHandReveal" in response.text
    response = client.get("/assets/styles.css")
    assert ".seat.is-folded .seat-state" in response.text
    assert ".card.is-back" in response.text
    assert ".play-actions button.danger" in response.text
