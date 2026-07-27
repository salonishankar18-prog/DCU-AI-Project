"""
run.py — start the Datum server.

    python run.py            serves the UI at http://localhost:8000
    python run.py --port N   on a different port

The API key is read from .env server-side. It never reaches the browser.
"""

import argparse
import os

import uvicorn
from dotenv import load_dotenv

load_dotenv()


def main():
    ap = argparse.ArgumentParser(description="Datum — floor plan dimension & access review")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8000)
    ap.add_argument("--reload", action="store_true", help="auto-reload on code changes")
    args = ap.parse_args()

    if not os.getenv("ANTHROPIC_API_KEY"):
        print("!  ANTHROPIC_API_KEY not set — Tab 1 works, Tab 2 will report it is unconfigured.")
        print("   Copy .env.example to .env and add your key.\n")

    print(f"   Datum  ->  http://{args.host}:{args.port}\n")
    uvicorn.run("api.main:app", host=args.host, port=args.port, reload=args.reload)


if __name__ == "__main__":
    main()
