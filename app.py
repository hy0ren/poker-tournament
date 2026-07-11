"""Vercel entrypoint for the FastAPI application."""

from webapp.server import app

__all__ = ["app"]
