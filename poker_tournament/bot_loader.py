"""Load workshop bots from Python files."""

from __future__ import annotations

import importlib.util
import os
import sys
from typing import Callable, List, Tuple


def load_bot(filepath: str) -> Tuple[str, Callable]:
    """Load one bot file and return ``(display_name, decide_function)``."""
    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Bot file not found: {filepath}")

    module_name = f"_poker_bot_{os.path.splitext(os.path.basename(filepath))[0]}"
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    if spec is None or spec.loader is None:
        raise ValueError(f"Could not import bot file: {filepath}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)

    decide = getattr(module, "decide", None)
    if not callable(decide):
        raise ValueError(f"{filepath} must define decide(game_state)")

    bot_name = getattr(module, "BOT_NAME", None)
    if not bot_name:
        bot_name = os.path.splitext(os.path.basename(filepath))[0]
    return str(bot_name), decide


def load_bots_from_directory(directory: str) -> List[Tuple[str, Callable]]:
    """Load every non-private ``*.py`` bot in a directory."""
    bots: List[Tuple[str, Callable]] = []
    for filename in sorted(os.listdir(directory)):
        if filename.endswith(".py") and not filename.startswith("_"):
            path = os.path.join(directory, filename)
            try:
                bots.append(load_bot(path))
            except Exception as exc:
                print(f"[warning] Skipping {filename}: {exc}")
    return bots
