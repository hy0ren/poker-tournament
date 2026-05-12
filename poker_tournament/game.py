"""Single-table Texas Hold'em engine with replay-friendly events."""

from __future__ import annotations

import random
import traceback
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .card import Card, Deck
from .hand_eval import evaluate_hand, hand_name
from .player import Player

VALID_ACTIONS = {"fold", "check", "call", "raise"}
MAX_SEATED_PLAYERS = 23


class PokerGame:
    """Play one table of no-limit Texas Hold'em."""

    def __init__(
        self,
        players: List[Player],
        small_blind: int = 10,
        big_blind: int = 20,
        verbose: bool = True,
        rng: Optional[random.Random] = None,
    ):
        if small_blind < 1 or big_blind <= small_blind:
            raise ValueError("Blinds must be positive and small_blind < big_blind")
        self.players = players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.verbose = verbose
        self.rng = rng or random.Random()

        self.community_cards: List[Card] = []
        self.pot = 0
        self.dealer_idx = 0
        self.hand_number = 0
        self._dealer_name = ""

    def play_hand(self) -> Optional[Dict[str, Any]]:
        """Play a hand and return a JSON-serializable result dictionary."""
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

        self._record(
            events,
            hand_players,
            "hand_start",
            f"Hand {self.hand_number}: {self._dealer_name} has the button.",
            "preflop",
            dealer=self._dealer_name,
        )

        self._post_blind(
            hand_players[small_blind_pos],
            self.small_blind,
            "small blind",
            hand_players,
            events,
        )
        self._post_blind(
            hand_players[big_blind_pos],
            self.big_blind,
            "big blind",
            hand_players,
            events,
        )

        for player in hand_players:
            player.hole_cards = deck.deal(2)
        self._record(
            events,
            hand_players,
            "deal",
            "Hole cards dealt.",
            "preflop",
        )

        opening_bet = max(player.current_bet for player in hand_players)
        self._betting_round(hand_players, "preflop", first_preflop, opening_bet, events)
        winner = self._single_remaining_player(hand_players)
        if winner is not None:
            return self._award_uncontested(winner, hand_players, events)

        streets = [
            ("flop", 3),
            ("turn", 1),
            ("river", 1),
        ]
        for street, cards_to_deal in streets:
            for player in hand_players:
                player.reset_for_street()
            dealt = deck.deal(cards_to_deal)
            if isinstance(dealt, list):
                self.community_cards.extend(dealt)
            else:
                self.community_cards.append(dealt)

            self._record(
                events,
                hand_players,
                "street",
                f"{street.title()}: {self._cards_text(self.community_cards)}",
                street,
            )
            first_to_act = self._first_to_act_after_dealer(hand_players)
            self._betting_round(hand_players, street, first_to_act, 0, events)

            winner = self._single_remaining_player(hand_players)
            if winner is not None:
                return self._award_uncontested(winner, hand_players, events)

        return self._showdown(hand_players, events)

    def _post_blind(
        self,
        player: Player,
        amount: int,
        label: str,
        hand_players: Sequence[Player],
        events: List[Dict[str, Any]],
    ) -> None:
        paid = player.commit(amount)
        self.pot += paid
        self._record(
            events,
            hand_players,
            "blind",
            f"{player.name} posts {paid} as the {label}.",
            "preflop",
            player=player.name,
            amount=paid,
            blind=label,
        )

    def _betting_round(
        self,
        players: Sequence[Player],
        street: str,
        first_to_act: int,
        opening_bet: int,
        events: List[Dict[str, Any]],
    ) -> None:
        current_bet = opening_bet
        pending = [
            index
            for index in self._seat_order(len(players), first_to_act)
            if players[index].can_act()
        ]

        while pending:
            if self._single_remaining_player(players) is not None:
                break

            index = pending.pop(0)
            player = players[index]
            if not player.can_act():
                continue

            call_amount = max(0, current_bet - player.current_bet)
            state = self._build_game_state(players, player, street, current_bet)
            action, amount = self._ask_bot(player, state)

            if action not in VALID_ACTIONS:
                action = "fold"
            if action == "check" and call_amount > 0:
                action = "call"
            if action == "call" and call_amount == 0:
                action = "check"

            if action == "fold":
                player.folded = True
                self._record(
                    events,
                    players,
                    "action",
                    f"{player.name} folds.",
                    street,
                    player=player.name,
                    action="fold",
                )
                continue

            if action == "check":
                self._record(
                    events,
                    players,
                    "action",
                    f"{player.name} checks.",
                    street,
                    player=player.name,
                    action="check",
                )
                continue

            if action == "call":
                paid = player.commit(call_amount)
                self.pot += paid
                suffix = " and is all-in" if player.all_in else ""
                self._record(
                    events,
                    players,
                    "action",
                    f"{player.name} calls {paid}{suffix}.",
                    street,
                    player=player.name,
                    action="call",
                    amount=paid,
                )
                continue

            raise_to = self._legal_raise_to(player, current_bet, amount)
            if raise_to <= current_bet:
                paid = player.commit(call_amount)
                self.pot += paid
                suffix = " and is all-in" if player.all_in else ""
                self._record(
                    events,
                    players,
                    "action",
                    f"{player.name} calls {paid}{suffix}.",
                    street,
                    player=player.name,
                    action="call",
                    amount=paid,
                )
                continue

            paid = player.commit(raise_to - player.current_bet)
            self.pot += paid
            current_bet = player.current_bet
            suffix = " and is all-in" if player.all_in else ""
            self._record(
                events,
                players,
                "action",
                f"{player.name} raises to {current_bet}{suffix}.",
                street,
                player=player.name,
                action="raise",
                amount=current_bet,
            )

            pending = [
                other_index
                for other_index in self._seat_order(len(players), index + 1)
                if players[other_index].can_act()
                and players[other_index].current_bet < current_bet
            ]

    def _ask_bot(self, player: Player, state: Dict[str, Any]) -> Tuple[str, int]:
        try:
            decision = player.bot_func(state)
            if isinstance(decision, str):
                return decision.lower().strip(), 0
            if isinstance(decision, (tuple, list)) and len(decision) == 2:
                action, amount = decision
                return str(action).lower().strip(), int(amount)
        except Exception:
            if self.verbose:
                print(f"[bot error] {player.name} folded after an exception:")
                traceback.print_exc()
        return "fold", 0

    def _build_game_state(
        self,
        players: Sequence[Player],
        me: Player,
        street: str,
        current_bet: int,
    ) -> Dict[str, Any]:
        return {
            "hole_cards": list(me.hole_cards),
            "community_cards": list(self.community_cards),
            "pot": self.pot,
            "current_bet": current_bet,
            "call_amount": max(0, current_bet - me.current_bet),
            "min_raise": self._minimum_raise_to(current_bet),
            "stack": me.stack,
            "my_bet": me.current_bet,
            "round": street,
            "big_blind": self.big_blind,
            "small_blind": self.small_blind,
            "hand_number": self.hand_number,
            "players": [
                {
                    "name": player.name,
                    "stack": player.stack,
                    "bet": player.current_bet,
                    "total_bet": player.total_bet,
                    "folded": player.folded,
                    "all_in": player.all_in,
                }
                for player in players
                if player is not me
            ],
        }

    def _award_uncontested(
        self,
        winner: Player,
        players: Sequence[Player],
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        pot_won = self.pot
        winner.stack += pot_won
        self.pot = 0
        self._record(
            events,
            players,
            "win",
            f"{winner.name} wins {pot_won}.",
            self._current_street(),
            winners=[winner.name],
            amount=pot_won,
            uncontested=True,
        )
        self.dealer_idx += 1
        return self._hand_result(players, events, [winner.name], uncontested=True)

    def _showdown(
        self,
        players: Sequence[Player],
        events: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        contenders = [player for player in players if not player.folded]
        hand_rows = []
        scores: Dict[str, Tuple[int, ...]] = {}
        for player in contenders:
            score = evaluate_hand(player.hole_cards + self.community_cards)
            scores[player.name] = score
            hand_rows.append(
                {
                    "name": player.name,
                    "cards": [card.to_dict() for card in player.hole_cards],
                    "hand": hand_name(score),
                    "score": list(score),
                }
            )

        self._record(
            events,
            players,
            "showdown",
            "Showdown.",
            "showdown",
            hands=hand_rows,
        )

        pot_results = []
        for amount, eligible in self._calculate_side_pots(players):
            live_eligible = [player for player in eligible if not player.folded]
            best = max(scores[player.name] for player in live_eligible)
            winners = [
                player
                for player in live_eligible
                if scores[player.name] == best
            ]
            share = amount // len(winners)
            remainder = amount % len(winners)
            for offset, winner in enumerate(winners):
                winner.stack += share + (1 if offset < remainder else 0)

            winner_names = [winner.name for winner in winners]
            self.pot = max(0, self.pot - amount)
            pot_results.append(
                {
                    "amount": amount,
                    "winners": winner_names,
                    "hand": hand_name(best),
                }
            )
            verb = "win" if len(winner_names) > 1 else "wins"
            self._record(
                events,
                players,
                "win",
                f"{', '.join(winner_names)} {verb} {amount} with {hand_name(best)}.",
                "showdown",
                winners=winner_names,
                amount=amount,
                hand=hand_name(best),
            )

        self.pot = 0
        self.dealer_idx += 1
        all_winners = []
        for result in pot_results:
            for name in result["winners"]:
                if name not in all_winners:
                    all_winners.append(name)
        return self._hand_result(players, events, all_winners, pots=pot_results)

    def _calculate_side_pots(
        self,
        players: Sequence[Player],
    ) -> List[Tuple[int, List[Player]]]:
        levels = sorted({player.total_bet for player in players if player.total_bet > 0})
        side_pots: List[Tuple[int, List[Player]]] = []
        previous = 0
        for level in levels:
            amount = sum(
                min(player.total_bet, level) - min(player.total_bet, previous)
                for player in players
            )
            eligible = [
                player
                for player in players
                if player.total_bet >= level and not player.folded
            ]
            if amount > 0 and eligible:
                side_pots.append((amount, eligible))
            previous = level
        return side_pots

    def _hand_result(
        self,
        players: Sequence[Player],
        events: List[Dict[str, Any]],
        winners: List[str],
        uncontested: bool = False,
        pots: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        return {
            "hand_number": self.hand_number,
            "dealer": self._dealer_name,
            "community_cards": [card.to_dict() for card in self.community_cards],
            "players": [player.public_state() for player in players],
            "winners": winners,
            "uncontested": uncontested,
            "pots": pots or [],
            "events": events,
        }

    def _legal_raise_to(self, player: Player, current_bet: int, requested: int) -> int:
        minimum = self._minimum_raise_to(current_bet)
        maximum = player.current_bet + player.stack
        if maximum <= current_bet:
            return maximum
        requested = max(int(requested), minimum)
        return min(requested, maximum)

    def _minimum_raise_to(self, current_bet: int) -> int:
        if current_bet == 0:
            return self.big_blind
        return current_bet + self.big_blind

    def _first_to_act_after_dealer(self, players: Sequence[Player]) -> int:
        for index in self._seat_order(len(players), self.dealer_idx + 1):
            if players[index].can_act():
                return index
        return 0

    def _single_remaining_player(self, players: Sequence[Player]) -> Optional[Player]:
        remaining = [player for player in players if not player.folded]
        if len(remaining) == 1:
            return remaining[0]
        return None

    def _seat_order(self, count: int, start: int) -> List[int]:
        return [(start + offset) % count for offset in range(count)]

    def _snapshot(self, players: Sequence[Player], street: str) -> Dict[str, Any]:
        return {
            "hand_number": self.hand_number,
            "street": street,
            "dealer": self._dealer_name,
            "pot": self.pot,
            "community_cards": [card.to_dict() for card in self.community_cards],
            "players": [player.public_state() for player in players],
            "small_blind": self.small_blind,
            "big_blind": self.big_blind,
        }

    def _record(
        self,
        events: List[Dict[str, Any]],
        players: Sequence[Player],
        kind: str,
        message: str,
        street: str,
        **data: Any,
    ) -> None:
        event = {
            "type": kind,
            "message": message,
            "snapshot": self._snapshot(players, street),
        }
        event.update(data)
        events.append(event)
        if self.verbose:
            print(message)

    def _cards_text(self, cards: Sequence[Card]) -> str:
        return " ".join(str(card) for card in cards)

    def _current_street(self) -> str:
        card_count = len(self.community_cards)
        if card_count == 0:
            return "preflop"
        if card_count == 3:
            return "flop"
        if card_count == 4:
            return "turn"
        if card_count == 5:
            return "river"
        return "showdown"
