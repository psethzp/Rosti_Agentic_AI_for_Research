"""CLI entrypoint for PDF ingestion."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.ingestion import ingest_dir
from app.utils import configure_logging


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Ingest PDFs into the vector store")
    parser.add_argument(
        "--input",
        required=True,
        help="Directory containing PDF files to ingest",
    )
    return parser.parse_args()


def main() -> None:
    configure_logging()
    args = parse_args()
    total = ingest_dir(args.input)
    logging.getLogger(__name__).info("Total chunks ingested: %d", total)
    print(f"Ingested {total} chunks from {args.input}")


if __name__ == "__main__":
    main()
