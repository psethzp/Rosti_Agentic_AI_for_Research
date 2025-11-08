"""Lightweight JSON cache for reviewer validations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import ensure_dirs

CACHE_DIR = Path(".data/cache")
CACHE_FILE = CACHE_DIR / "reviewer_cache.json"
ensure_dirs(CACHE_DIR)

_CACHE: Optional[Dict[str, Any]] = None


def _load_cache() -> Dict[str, Any]:
    global _CACHE
    if _CACHE is None:
        if CACHE_FILE.exists():
            try:
                _CACHE = json.loads(CACHE_FILE.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                _CACHE = {}
        else:
            _CACHE = {}
    return _CACHE


def cache_get(key: str) -> Optional[Any]:
    data = _load_cache()
    return data.get(key)


def cache_set(key: str, value: Any) -> None:
    data = _load_cache()
    data[key] = value
    CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
