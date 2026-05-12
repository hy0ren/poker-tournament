#!/usr/bin/env python3
"""Run a poker bot tournament from the command line."""

from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from poker_tournament import MAX_BOTS, Tournament, load_bot, load_bots_from_directory


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a Texas Hold'em bot tournament.")
    parser.add_argument("bots", nargs="+", help="Bot .py files or directories of bots.")
    parser.add_argument("--mode", choices=["fixed", "elimination"], default="fixed")
    parser.add_argument("--hands", type=int, default=25, help="Maximum hands to play.")
    parser.add_argument("--chips", type=int, default=1000, help="Starting chips per bot.")
    parser.add_argument("--small-blind", type=int, default=10)
    parser.add_argument("--big-blind", type=int, default=20)
    parser.add_argument("--seed", type=int, default=None, help="Optional deterministic seed.")
    parser.add_argument("--quiet", "-q", action="store_true", help="Only print standings.")
    return parser.parse_args()


def load_all_bots(paths):
    bots = []
    for path in paths:
        if os.path.isdir(path):
            bots.extend(load_bots_from_directory(path))
        elif os.path.isfile(path):
            bots.append(load_bot(path))
        else:
            raise SystemExit(f"Path not found: {path}")
    if len(bots) < 2:
        raise SystemExit("At least two bots are required.")
    if len(bots) > MAX_BOTS:
        raise SystemExit(
            f"At most {MAX_BOTS} bots can play in one tournament. "
            "Pass specific bot files instead of the whole directory."
        )
    return bots


def main() -> None:
    args = parse_args()
    bots = load_all_bots(args.bots)
    tournament = Tournament(
        bots=bots,
        starting_chips=args.chips,
        small_blind=args.small_blind,
        big_blind=args.big_blind,
        mode=args.mode,
        num_hands=args.hands,
        verbose=not args.quiet,
        seed=args.seed,
    )
    standings = tournament.run()
    tournament.print_results(standings)


if __name__ == "__main__":
    main()
