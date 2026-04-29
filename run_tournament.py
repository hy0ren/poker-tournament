#!/usr/bin/env python3
"""
run_tournament.py — CLI entry point for the poker bot tournament.

Usage examples
--------------
# Run all four example bots in an elimination tournament:
  python run_tournament.py bots/random_bot.py bots/call_bot.py \
                           bots/aggressive_bot.py bots/smart_bot.py

# Load every bot from a directory:
  python run_tournament.py bots/

# Fixed number of hands, quiet output:
  python run_tournament.py bots/ --mode fixed --hands 500 --quiet

# Custom chip stacks and blinds:
  python run_tournament.py bots/ --chips 2000 --small-blind 25 --big-blind 50
"""

import argparse
import os
import sys

# Make sure the package is importable when run from the repo root.
sys.path.insert(0, os.path.dirname(__file__))

from poker_tournament import Tournament, load_bot, load_bots_from_directory


def parse_args():
    parser = argparse.ArgumentParser(
        description='Run a poker bot tournament.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        'bots',
        nargs='+',
        metavar='BOT',
        help=(
            'Paths to bot Python files (e.g. my_bot.py) or a single directory '
            'containing bot files.'
        ),
    )
    parser.add_argument(
        '--mode',
        choices=['elimination', 'fixed'],
        default='elimination',
        help=(
            'Tournament mode: "elimination" (play until one player holds all '
            'chips) or "fixed" (play a set number of hands). Default: elimination.'
        ),
    )
    parser.add_argument(
        '--hands',
        type=int,
        default=1000,
        metavar='N',
        help='Number of hands for "fixed" mode. Default: 1000.',
    )
    parser.add_argument(
        '--chips',
        type=int,
        default=1000,
        metavar='N',
        help='Starting chip stack per player. Default: 1000.',
    )
    parser.add_argument(
        '--small-blind',
        type=int,
        default=10,
        metavar='N',
        help='Small blind amount. Default: 10.',
    )
    parser.add_argument(
        '--big-blind',
        type=int,
        default=20,
        metavar='N',
        help='Big blind amount. Default: 20.',
    )
    parser.add_argument(
        '--quiet', '-q',
        action='store_true',
        help='Suppress hand-by-hand output; only show final standings.',
    )
    return parser.parse_args()


def load_all_bots(paths):
    """Resolve paths to (name, func) pairs."""
    bots = []
    for path in paths:
        if os.path.isdir(path):
            found = load_bots_from_directory(path)
            if not found:
                print(f"[WARNING] No bot files found in directory: {path}")
            bots.extend(found)
        elif os.path.isfile(path):
            try:
                bots.append(load_bot(path))
            except Exception as exc:
                print(f"[ERROR] Could not load bot {path}: {exc}")
                sys.exit(1)
        else:
            print(f"[ERROR] Path not found: {path}")
            sys.exit(1)
    return bots


def main():
    args = parse_args()

    bots = load_all_bots(args.bots)
    if len(bots) < 2:
        print("[ERROR] At least 2 bots are required to run a tournament.")
        sys.exit(1)

    # Deduplicate names (append index if two bots share the same name)
    seen: dict = {}
    unique_bots = []
    for name, func in bots:
        count = seen.get(name, 0)
        seen[name] = count + 1
        display_name = name if count == 0 else f"{name}_{count + 1}"
        unique_bots.append((display_name, func))

    print(f"\nPoker Tournament — {len(unique_bots)} bots")
    print(f"Mode: {args.mode}  |  Starting chips: {args.chips}  |  "
          f"Blinds: {args.small_blind}/{args.big_blind}")
    print("Bots: " + ", ".join(name for name, _ in unique_bots))

    tournament = Tournament(
        bots=unique_bots,
        starting_chips=args.chips,
        small_blind=args.small_blind,
        big_blind=args.big_blind,
        mode=args.mode,
        num_hands=args.hands,
        verbose=not args.quiet,
    )

    standings = tournament.run()
    tournament.print_results(standings)


if __name__ == '__main__':
    main()
