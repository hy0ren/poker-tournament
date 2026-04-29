"""Bot loader — imports a Python file and extracts a decide() function."""

import importlib.util
import os
import sys
from typing import Callable, Tuple


def load_bot(filepath: str) -> Tuple[str, Callable]:
    """
    Load a poker bot from *filepath*.

    The file must define a ``decide(game_state)`` function that returns
    ``(action, amount)`` (see README for the full interface).
    An optional module-level ``BOT_NAME`` string gives the bot a display name.

    Returns:
        (bot_name, decide_func)

    Raises:
        ValueError: if the file has no ``decide`` function.
        FileNotFoundError: if *filepath* does not exist.
    """
    filepath = os.path.abspath(filepath)
    if not os.path.isfile(filepath):
        raise FileNotFoundError(f"Bot file not found: {filepath}")

    module_name = f"_bot_{os.path.splitext(os.path.basename(filepath))[0]}"
    spec = importlib.util.spec_from_file_location(module_name, filepath)
    module = importlib.util.module_from_spec(spec)   # type: ignore[arg-type]
    sys.modules[module_name] = module
    spec.loader.exec_module(module)                  # type: ignore[union-attr]

    if not hasattr(module, 'decide') or not callable(module.decide):
        raise ValueError(
            f"{filepath} must define a callable 'decide(game_state)' function"
        )

    bot_name = getattr(module, 'BOT_NAME', None) or os.path.splitext(
        os.path.basename(filepath)
    )[0]

    return str(bot_name), module.decide


def load_bots_from_directory(directory: str) -> list:
    """
    Load all ``*.py`` bot files from *directory* (non-recursive).

    Returns:
        List of (bot_name, decide_func) tuples.
    """
    bots = []
    for filename in sorted(os.listdir(directory)):
        if filename.endswith('.py') and not filename.startswith('_'):
            path = os.path.join(directory, filename)
            try:
                bots.append(load_bot(path))
            except Exception as exc:
                print(f"[WARNING] Could not load {path}: {exc}")
    return bots
