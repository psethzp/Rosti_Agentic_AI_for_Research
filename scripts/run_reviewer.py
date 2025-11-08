"""CLI to run the Reviewer agent on saved claims."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents import load_claims_from_artifacts, run_reviewer, run_synthesizer
from app.schemas import Claim, ReviewedClaim
from app.utils import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Review claims with span validation")
    parser.add_argument(
        "--claims",
        default=None,
        help="Optional path to claims.json (defaults to artifacts/claims.json)",
    )
    parser.add_argument(
        "--topic",
        default=None,
        help="Optional topic override for synthesizer (defaults to claims' topic)",
    )
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()

    if args.claims:
        path = Path(args.claims).expanduser()
        if not path.exists():
            raise FileNotFoundError(f"{path} not found")
        data = path.read_text(encoding="utf-8")
        import json

        claims = [Claim.model_validate(item) for item in json.loads(data)]
    else:
        claims = load_claims_from_artifacts()

    reviewed = run_reviewer(claims)
    logging.getLogger(__name__).info("Reviewed %d claims", len(reviewed))
    for claim in reviewed:
        print(f"{claim.id}: {claim.verdict} ({claim.reviewer_notes})")
    topic = args.topic or (claims[0].topic if claims else "Untitled Topic")
    insights = run_synthesizer(topic, reviewed)
    logging.getLogger(__name__).info("Synthesized %d insights", len(insights))
    print("Saved output to artifacts/claims_reviewed.json and artifacts/report.{json,html}")


if __name__ == "__main__":
    main()
