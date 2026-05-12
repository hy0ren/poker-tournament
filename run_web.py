#!/usr/bin/env python3
"""Launch the poker tournament web UI.

Usage:
    python run_web.py                 # http://127.0.0.1:8000
    python run_web.py --port 9000
    python run_web.py --host 0.0.0.0  # expose on the LAN
"""

import argparse
import os
import sys


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the poker tournament web UI.")
    parser.add_argument("--host", default="127.0.0.1", help="Bind address (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Bind port (default: 8000)")
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Auto-reload on code changes (dev only).",
    )
    args = parser.parse_args()

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    try:
        import uvicorn
    except ImportError:
        print(
            "[ERROR] uvicorn is not installed.\n"
            "Install the web extras with:  pip install -r requirements.txt",
            file=sys.stderr,
        )
        sys.exit(1)

    uvicorn.run(
        "webapp.server:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
    )


if __name__ == "__main__":
    main()
