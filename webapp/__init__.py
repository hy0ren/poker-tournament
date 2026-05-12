"""FastAPI web UI for the poker tournament engine.

This package wraps the existing ``poker_tournament`` library with an
HTTP API and a small static frontend.  The poker engine itself is
imported untouched.
"""

from .server import app, create_app  # noqa: F401

__all__ = ["app", "create_app"]
