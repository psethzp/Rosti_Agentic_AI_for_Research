"""Utility helpers for paths and logging."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable


def ensure_dirs(*paths: str | Path | Iterable[str | Path]) -> None:
    """Create directories if they do not exist."""
    flat: list[str | Path] = []
    for item in paths:
        if isinstance(item, (list, tuple, set)):
            flat.extend(item)
        else:
            flat.append(item)
    for raw_path in flat:
        path = Path(raw_path).expanduser()
        if not path.exists():
            path.mkdir(parents=True, exist_ok=True)


def configure_logging() -> None:
    """Ensure logging has at least a basic configuration."""
    if not logging.getLogger().handlers:
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        )
