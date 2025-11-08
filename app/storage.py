"""Helpers for caching and retrieving source page text."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

from .utils import ensure_dirs

TEXT_CACHE_DIR = Path(os.getenv("TEXT_CACHE_DIR", ".data/page_cache")).expanduser()
ensure_dirs(TEXT_CACHE_DIR)


def cache_page_texts(source_id: str, pages: List[Dict]) -> Path:
    """Persist raw page text for later validation."""
    payload = [
        {"page": page["page"], "text": page.get("text", "")}
        for page in pages
        if page.get("text")
    ]
    target = TEXT_CACHE_DIR / f"{source_id}.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_page_text(source_id: str, page: int) -> Optional[str]:
    """Return the cached text for a given source/page if available."""
    path = TEXT_CACHE_DIR / f"{source_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    for entry in data:
        if entry.get("page") == page:
            return entry.get("text")
    return None
