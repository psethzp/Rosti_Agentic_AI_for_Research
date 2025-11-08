"""CLI to execute the Researcher agent and dump claims."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents import run_researcher
from app.utils import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate claims for a topic")
    parser.add_argument("--topic", required=True, help="Topic/question for the Researcher agent")
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    claims = run_researcher(args.topic)
    logging.getLogger(__name__).info("Generated %d claims", len(claims))
    for claim in claims:
        citation = claim.citations[0] if claim.citations else None
        evidence = (
            f"{citation.source_id} p{citation.page}"
            if citation
            else "no-citation"
        )
        print(f"{claim.id}: {claim.text} [{evidence}]")
    print("Saved artifacts to artifacts/claims.json")


if __name__ == "__main__":
    main()
