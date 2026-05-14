"""Stateful browser play sessions for a human poker seat."""

from __future__ import annotations

import random
import uuid
from typing import Any, Callable, Dict, Generator, List, Optional, Sequence, Tuple

from poker_tournament.card import Card, Deck
from poker_tournament.game import MAX_SEATED_PLAYERS, VALID_ACTIONS, PokerGame
from poker_tournament.hand_eval import evaluate_hand, hand_name
from poker_tournament.player import Player

HUMAN_NAME = "You"


class PlaySession:
    """Pause/resume Hold'em session with one human player and bot opponents."""

    def __init__(
        self,
        bots: List[Tuple[str, Callable]],
        starting_chips: int,
        small_blind: int,
        big_blind: int,
        num_hands: int,
        seed: Optional[int],
    ):
        self.id = uuid.uuid4().hex
        self.starting_chips = starting_chips
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.num_hands = num_hands
        self.rng = random.Random(seed)
        self.players = [Player(HUMAN_NAME, starting_chips, _human_placeholder)]
        self.players.extend(Player(name, starting_chips, decide) for name, decide in _unique_bots(bots))
        self.hands: List[Dict[str, Any]] = []
        self.events: List[Dict[str, Any]] = []
        self.pending: Optional[Dict[str, Any]] = None
        self._game = InteractivePokerGame(
            self.players,
            human_name=HUMAN_NAME,
            small_blind=small_blind,
            big_blind=big_blind,
            verbose=False,
            rng=self.rng,
        )
        self._runner: Optional[Generator] = None

    def start(self) -> Dict[str, Any]:
        return self._continue(None)

    def act(self, action: str, amount: int = 0) -> Dict[str, Any]:
        if self.pending is None:
            return self._payload(done=self._done())
        action = action.lower().strip()
        if action not in VALID_ACTIONS:
            action = "fold"
        return self._continue((action, int(amount or 0)))

    def _continue(self, decision: Optional[Tuple[str, int]]) -> Dict[str, Any]:
        while not self._done():
            if self._runner is None:
                self._runner = self._game.play_hand_interactive()
                decision = None
            try:
                self.pending = self._runner.send(decision)
                return self._payload(done=False)
            except StopIteration as finished:
                self._runner = None
                self.pending = None
                result = finished.value
                if result is None:
                    break
                self._append_reveal_event(result)
                self.hands.append(result)
                self.events.extend(result["events"])
                decision = None
        return self._payload(done=True)

    def _done(self) -> bool:
        active = [player for player in self.players if player.stack > 0]
        return len(active) < 2 or len(self.hands) >= self.num_hands

    def _payload(self, done: bool) -> Dict[str, Any]:
        events = [event for hand in self.hands for event in hand["events"]]
        if self._game.current_events:
            events.extend(self._game.current_events)
        snapshot = self._live_snapshot(events)
        if done and (not events or events[-1]["type"] != "play_complete"):
            events.append(
                {
                    "type": "play_complete",
                    "message": "Play session complete.",
                    "snapshot": snapshot,
                }
            )
        return {
            "session_id": self.id,
            "pending": self.pending,
            "done": done,
            "events": events,
            "snapshot": snapshot,
            "hands_played": len(self.hands),
            "standings": _standings(self.players, len(self.hands)),
        }

    def _live_snapshot(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        if self.pending is not None:
            return self.pending["snapshot"]
        for event in reversed(events):
            snapshot = event.get("snapshot")
            if snapshot and snapshot.get("street") != "complete":
                return snapshot
        return self._game.final_snapshot(len(self.hands))

    def _append_reveal_event(self, result: Dict[str, Any]) -> None:
        snapshot = {
            "hand_number": result["hand_number"],
            "street": "showdown",
            "dealer": result["dealer"],
            "pot": 0,
            "community_cards": result["community_cards"],
            "players": result["players"],
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
        }
        result["events"].append(
            {
                "type": "reveal",
                "message": "Hand complete. All hole cards are revealed.",
                "snapshot": snapshot,
            }
        )


class InteractivePokerGame(PokerGame):
    def __init__(self, players: List[Player], human_name: str, **kwargs: Any):
        super().__init__(players, **kwargs)
        self.human_name = human_name
        self.current_events: List[Dict[str, Any]] = []

    def play_hand_interactive(self) -> Generator[Dict[str, Any], Optional[Tuple[str, int]], Optional[Dict[str, Any]]]:
        live_players = [player for player in self.players if player.stack > 0]
        if len(live_players) > MAX_SEATED_PLAYERS:
            start = self.dealer_idx % len(live_players)
            rotated = live_players[start:] + live_players[:start]
            hand_players = rotated[:MAX_SEATED_PLAYERS]
        else:
            hand_players = live_players
        if len(hand_players) < 2:
            return None

        self.hand_number += 1
        self.community_cards = []
        self.pot = 0
        events: List[Dict[str, Any]] = []
        self.current_events = events

        for player in hand_players:
            player.reset_for_hand()

        deck = Deck(self.rng)
        player_count = len(hand_players)
        dealer_pos = 0 if len(live_players) > MAX_SEATED_PLAYERS else self.dealer_idx % player_count
        self._dealer_name = hand_players[dealer_pos].name

        if player_count == 2:
            small_blind_pos = dealer_pos
            big_blind_pos = (dealer_pos + 1) % player_count
            first_preflop = dealer_pos
        else:
            small_blind_pos = (dealer_pos + 1) % player_count
            big_blind_pos = (dealer_pos + 2) % player_count
            first_preflop = (big_blind_pos + 1) % player_count

        self._record(events, hand_players, "hand_start", f"Hand {self.hand_number}: {self._dealer_name} has the button.", "preflop", dealer=self._dealer_name)
        self._post_blind(hand_players[small_blind_pos], self.small_blind, "small blind", hand_players, events)
        self._post_blind(hand_players[big_blind_pos], self.big_blind, "big blind", hand_players, events)

        for player in hand_players:
            player.hole_cards = deck.deal(2)
        self._record(events, hand_players, "deal", "Hole cards dealt.", "preflop")

        opening_bet = max(player.current_bet for player in hand_players)
        yield from self._betting_round_interactive(hand_players, "preflop", first_preflop, opening_bet, events)
        winner = self._single_remaining_player(hand_players)
        if winner is not None:
            result = self._award_uncontested(winner, hand_players, events)
            self.current_events = []
            return result

        for street, cards_to_deal in [("flop", 3), ("turn", 1), ("river", 1)]:
            for player in hand_players:
                player.reset_for_street()
            dealt = deck.deal(cards_to_deal)
            self.community_cards.extend(dealt if isinstance(dealt, list) else [dealt])
            self._record(events, hand_players, "street", f"{street.title()}: {self._cards_text(self.community_cards)}", street)
            yield from self._betting_round_interactive(hand_players, street, self._first_to_act_after_dealer(hand_players), 0, events)
            winner = self._single_remaining_player(hand_players)
            if winner is not None:
                result = self._award_uncontested(winner, hand_players, events)
                self.current_events = []
                return result

        result = self._showdown(hand_players, events)
        self.current_events = []
        return result

    def _betting_round_interactive(
        self,
        players: Sequence[Player],
        street: str,
        first_to_act: int,
        opening_bet: int,
        events: List[Dict[str, Any]],
    ) -> Generator[Dict[str, Any], Optional[Tuple[str, int]], None]:
        current_bet = opening_bet
        pending = [index for index in self._seat_order(len(players), first_to_act) if players[index].can_act()]

        while pending:
            if self._single_remaining_player(players) is not None:
                break
            index = pending.pop(0)
            player = players[index]
            if not player.can_act():
                continue

            call_amount = max(0, current_bet - player.current_bet)
            state = self._build_game_state(players, player, street, current_bet)
            if player.name == self.human_name:
                decision = yield {
                    "player": player.name,
                    "state": state,
                    "legal_actions": _legal_actions(call_amount, player.stack),
                    "snapshot": self._snapshot(players, street),
                }
                action, amount = decision or ("fold", 0)
            else:
                action, amount = self._ask_bot(player, state)

            if action not in VALID_ACTIONS:
                action = "fold"
            if action == "check" and call_amount > 0:
                action = "call"
            if action == "call" and call_amount == 0:
                action = "check"

            if action == "fold":
                player.folded = True
                self._record(events, players, "action", f"{player.name} folds.", street, player=player.name, action="fold")
                continue
            if action == "check":
                self._record(events, players, "action", f"{player.name} checks.", street, player=player.name, action="check")
                continue
            if action == "call":
                paid = player.commit(call_amount)
                self.pot += paid
                suffix = " and is all-in" if player.all_in else ""
                self._record(events, players, "action", f"{player.name} calls {paid}{suffix}.", street, player=player.name, action="call", amount=paid)
                continue

            raise_to = self._legal_raise_to(player, current_bet, amount)
            if raise_to <= current_bet:
                paid = player.commit(call_amount)
                self.pot += paid
                suffix = " and is all-in" if player.all_in else ""
                self._record(events, players, "action", f"{player.name} calls {paid}{suffix}.", street, player=player.name, action="call", amount=paid)
                continue

            paid = player.commit(raise_to - player.current_bet)
            self.pot += paid
            current_bet = player.current_bet
            suffix = " and is all-in" if player.all_in else ""
            self._record(events, players, "action", f"{player.name} raises to {current_bet}{suffix}.", street, player=player.name, action="raise", amount=current_bet)
            pending = [
                other_index
                for other_index in self._seat_order(len(players), index + 1)
                if players[other_index].can_act() and players[other_index].current_bet < current_bet
            ]

    def final_snapshot(self, hand_count: int) -> Dict[str, Any]:
        return {
            "hand_number": hand_count,
            "street": "complete",
            "dealer": "",
            "pot": 0,
            "community_cards": [],
            "players": [player.public_state() for player in self.players],
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
        }

    def _snapshot(self, players: Sequence[Player], street: str) -> Dict[str, Any]:
        reveal_all = street in {"showdown", "complete"}
        return {
            "hand_number": self.hand_number,
            "street": street,
            "dealer": self._dealer_name,
            "pot": self.pot,
            "community_cards": [card.to_dict() for card in self.community_cards],
            "players": [
                player.public_state(reveal_cards=reveal_all or player.name == self.human_name)
                for player in players
            ],
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
        }


def _human_placeholder(game_state: Dict[str, Any]) -> Tuple[str, int]:
    return "fold", 0


def _legal_actions(call_amount: int, stack: int) -> List[str]:
    actions = ["fold"]
    actions.append("check" if call_amount == 0 else "call")
    if stack > call_amount:
        actions.append("raise")
    return actions


def _unique_bots(bots: List[Tuple[str, Callable]]) -> List[Tuple[str, Callable]]:
    seen: Dict[str, int] = {}
    unique = []
    for name, decide in bots:
        count = seen.get(name, 0) + 1
        seen[name] = count
        unique.append((name if count == 1 else f"{name} {count}", decide))
    return unique


def _standings(players: List[Player], hands_played: int) -> List[Dict[str, Any]]:
    ranked = sorted(players, key=lambda player: (-player.stack, player.name))
    return [
        {
            "rank": index + 1,
            "name": player.name,
            "chips": player.stack,
            "hands_played": hands_played,
            "status": "active" if player.stack > 0 else "out",
        }
        for index, player in enumerate(ranked)
    ]
