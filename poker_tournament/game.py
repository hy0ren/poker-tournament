"""Texas Hold'em game engine."""

import traceback
from typing import Any, Dict, List, Optional, Tuple

from .card import Deck, Card
from .hand_eval import evaluate_hand, hand_name
from .player import Player


class PokerGame:
    """Single-table Texas Hold'em engine."""

    def __init__(
        self,
        players: List[Player],
        small_blind: int = 10,
        big_blind: int = 20,
        verbose: bool = True,
    ):
        self.players = players
        self.small_blind = small_blind
        self.big_blind = big_blind
        self.verbose = verbose

        self.community_cards: List[Card] = []
        self.pot: int = 0
        self.dealer_idx: int = 0
        self.hand_number: int = 0

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    def play_hand(self) -> Optional[Dict]:
        """Play one hand. Returns a result dict, or None if < 2 players remain."""
        active = [p for p in self.players if p.stack > 0]
        if len(active) < 2:
            return None

        self.hand_number += 1
        for p in active:
            p.reset_for_hand()

        self.community_cards = []
        self.pot = 0
        deck = Deck()
        n = len(active)

        # ---- Blinds ----
        dealer_pos = self.dealer_idx % n
        if n == 2:
            # Heads-up: dealer == small blind
            sb_pos = dealer_pos
            bb_pos = (dealer_pos + 1) % n
        else:
            sb_pos = (dealer_pos + 1) % n
            bb_pos = (dealer_pos + 2) % n

        sb, bb = active[sb_pos], active[bb_pos]
        self._log(
            f"\n{'='*55}\n"
            f"Hand #{self.hand_number}  "
            f"Dealer: {active[dealer_pos].name}  "
            f"SB: {sb.name}({self.small_blind})  "
            f"BB: {bb.name}({self.big_blind})"
        )
        self.pot += sb.bet(self.small_blind)
        self.pot += bb.bet(self.big_blind)

        # ---- Deal hole cards ----
        for p in active:
            p.hole_cards = deck.deal(2)

        self._log(f"Pot after blinds: {self.pot}")
        self._log_stacks(active)

        # ---- Pre-flop ----
        first_act = sb_pos if n == 2 else (bb_pos + 1) % n
        self._betting_round(active, 'preflop', first_act, self.big_blind)

        remaining = [p for p in active if not p.folded]
        if len(remaining) == 1:
            return self._award_uncontested(remaining[0])

        # ---- Flop ----
        self.community_cards = deck.deal(3)
        self._log(f"\nFlop: {self.community_cards}")
        for p in active:
            p.reset_for_round()
        first_act = self._first_active_after_dealer(active)
        self._betting_round(active, 'flop', first_act, 0)

        remaining = [p for p in active if not p.folded]
        if len(remaining) == 1:
            return self._award_uncontested(remaining[0])

        # ---- Turn ----
        self.community_cards.append(deck.deal())
        self._log(f"Turn:  {self.community_cards}")
        for p in active:
            p.reset_for_round()
        first_act = self._first_active_after_dealer(active)
        self._betting_round(active, 'turn', first_act, 0)

        remaining = [p for p in active if not p.folded]
        if len(remaining) == 1:
            return self._award_uncontested(remaining[0])

        # ---- River ----
        self.community_cards.append(deck.deal())
        self._log(f"River: {self.community_cards}")
        for p in active:
            p.reset_for_round()
        first_act = self._first_active_after_dealer(active)
        self._betting_round(active, 'river', first_act, 0)

        remaining = [p for p in active if not p.folded]
        if len(remaining) == 1:
            return self._award_uncontested(remaining[0])

        return self._showdown(remaining, active)

    # ------------------------------------------------------------------
    # Betting round
    # ------------------------------------------------------------------

    def _betting_round(
        self,
        players: List[Player],
        round_name: str,
        first_to_act_idx: int,
        opening_bet: int,
    ) -> None:
        n = len(players)
        current_bet = opening_bet

        # Build an ordered list of player indices who need to act this street.
        # After a raise, this list is replaced with all players who must re-act.
        to_act: List[int] = []
        for i in range(n):
            j = (first_to_act_idx + i) % n
            p = players[j]
            if not p.folded and not p.all_in and p.stack > 0:
                to_act.append(j)

        self._log(f"\n--- {round_name.upper()} ---  Pot: {self.pot}  Bet: {current_bet}")

        while to_act:
            # If only one player hasn't folded, betting is over
            if sum(1 for p in players if not p.folded) <= 1:
                break

            idx = to_act.pop(0)
            p = players[idx]

            # The player may have gone all-in or folded since being queued
            if p.folded or p.all_in:
                continue

            call_amount = max(0, current_bet - p.current_bet)
            game_state = self._build_game_state(players, p, round_name, current_bet)
            action, amount = self._get_action(p, game_state)

            # Normalise: if bot tries to check when there is a bet, treat as call
            if action == 'check' and call_amount > 0:
                action = 'call'

            if action == 'fold':
                p.folded = True
                self._log(f"  {p.name} folds")

            elif action in ('check', 'call'):
                if call_amount > 0:
                    paid = p.bet(call_amount)
                    self.pot += paid
                    status = " (all-in)" if p.all_in else ""
                    self._log(f"  {p.name} calls {paid}{status}  [stack: {p.stack}]")
                else:
                    self._log(f"  {p.name} checks")

            elif action == 'raise':
                # Minimum raise = current_bet + big_blind (or current_bet if heads-up)
                min_raise_to = current_bet + max(self.big_blind, current_bet)
                if current_bet == 0:
                    min_raise_to = self.big_blind  # opening bet post-flop
                raise_to = max(amount if amount > current_bet else min_raise_to,
                               min_raise_to)
                # Can't raise more than stack allows
                raise_to = min(raise_to, p.stack + p.current_bet)
                add = raise_to - p.current_bet
                paid = p.bet(add)
                self.pot += paid

                if p.current_bet > current_bet:
                    current_bet = p.current_bet
                    status = " (all-in)" if p.all_in else ""
                    self._log(
                        f"  {p.name} raises to {current_bet}{status}  [stack: {p.stack}]"
                    )
                    # All other active players must act again (in seat order after raiser)
                    to_act = [
                        (idx + offset) % n
                        for offset in range(1, n)
                        if not players[(idx + offset) % n].folded
                        and not players[(idx + offset) % n].all_in
                        and players[(idx + offset) % n].stack > 0
                    ]
                else:
                    # Couldn't actually raise (e.g. short-stack all-in)
                    status = " (all-in)" if p.all_in else ""
                    self._log(f"  {p.name} calls {paid}{status}  [stack: {p.stack}]")

            else:
                # Unknown action → default to fold
                p.folded = True
                self._log(f"  {p.name} folds (unrecognised action: {action!r})")

    # ------------------------------------------------------------------
    # Bot execution
    # ------------------------------------------------------------------

    def _get_action(self, player: Player, game_state: Dict) -> Tuple[str, int]:
        """Invoke the bot's decide() function safely."""
        try:
            result = player.bot_func(game_state)
            if isinstance(result, (list, tuple)) and len(result) == 2:
                action, amount = result
                return str(action).lower().strip(), int(amount)
            if isinstance(result, str):
                return result.lower().strip(), 0
        except Exception:
            self._log(f"  [ERROR] {player.name} raised an exception — folding:")
            traceback.print_exc()
        return 'fold', 0

    def _build_game_state(
        self,
        players: List[Player],
        me: Player,
        round_name: str,
        current_bet: int,
    ) -> Dict[str, Any]:
        """Construct the state dict handed to each bot."""
        others = [
            {
                'name': p.name,
                'stack': p.stack,
                'bet': p.current_bet,
                'total_bet': p.total_bet,
                'folded': p.folded,
                'all_in': p.all_in,
            }
            for p in players
            if p is not me
        ]
        return {
            'hole_cards': list(me.hole_cards),
            'community_cards': list(self.community_cards),
            'pot': self.pot,
            'current_bet': current_bet,
            'call_amount': max(0, current_bet - me.current_bet),
            'min_raise': current_bet + max(self.big_blind, current_bet or self.big_blind),
            'stack': me.stack,
            'my_bet': me.current_bet,
            'round': round_name,
            'players': others,
            'big_blind': self.big_blind,
            'small_blind': self.small_blind,
        }

    # ------------------------------------------------------------------
    # Pot distribution
    # ------------------------------------------------------------------

    def _award_uncontested(self, winner: Player) -> Dict:
        """One player remains — award them the full pot."""
        winner.stack += self.pot
        self._log(f"\n{winner.name} wins {self.pot} (everyone else folded)")
        result = {
            'winners': [winner.name],
            'pot': self.pot,
            'uncontested': True,
        }
        self.pot = 0
        self.dealer_idx += 1
        return result

    def _showdown(self, remaining: List[Player], all_players: List[Player]) -> Dict:
        """Evaluate hands, distribute side pots, advance the dealer button."""
        self._log("\n--- SHOWDOWN ---")
        side_pots = self._calculate_side_pots(all_players)
        pot_results = []

        for pot_amount, eligible in side_pots:
            contenders = [p for p in eligible if not p.folded]
            if not contenders:
                continue

            scored = []
            for p in contenders:
                score = evaluate_hand(p.hole_cards + self.community_cards)
                scored.append((p, score))
                self._log(
                    f"  {p.name}: {p.hole_cards}  →  {hand_name(score)}"
                )

            best = max(s for _, s in scored)
            winners = [p for p, s in scored if s == best]
            split = pot_amount // len(winners)
            remainder = pot_amount % len(winners)

            for i, w in enumerate(winners):
                gain = split + (remainder if i == 0 else 0)
                w.stack += gain
                self._log(f"  ✓ {w.name} wins {gain} ({hand_name(best)})")

            pot_results.append({
                'pot': pot_amount,
                'winners': [w.name for w in winners],
                'hand': hand_name(best),
            })

        self.pot = 0
        self.dealer_idx += 1
        all_winners = list({n for r in pot_results for n in r['winners']})
        return {
            'pots': pot_results,
            'winners': all_winners,
            'community_cards': self.community_cards,
        }

    def _calculate_side_pots(
        self, players: List[Player]
    ) -> List[Tuple[int, List[Player]]]:
        """
        Calculate side pots from total bets.

        Returns a list of (pot_amount, eligible_players) sorted from
        smallest all-in level to largest.
        """
        levels = sorted({p.total_bet for p in players if p.total_bet > 0})
        side_pots: List[Tuple[int, List[Player]]] = []
        prev = 0

        for level in levels:
            # Each player contributes min(their_total_bet, level) − prev
            amount = sum(
                min(p.total_bet, level) - min(p.total_bet, prev)
                for p in players
            )
            # Eligible: contributed at this level AND haven't folded
            eligible = [p for p in players if p.total_bet >= level and not p.folded]
            if amount > 0:
                side_pots.append((amount, eligible))
            prev = level

        return side_pots

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _first_active_after_dealer(self, players: List[Player]) -> int:
        n = len(players)
        for i in range(1, n + 1):
            idx = (self.dealer_idx + i) % n
            if not players[idx].folded:
                return idx
        return 0

    def _log(self, msg: str) -> None:
        if self.verbose:
            print(msg)

    def _log_stacks(self, players: List[Player]) -> None:
        if self.verbose:
            parts = [f"{p.name}:{p.stack}" for p in players]
            print("  Stacks: " + "  ".join(parts))
