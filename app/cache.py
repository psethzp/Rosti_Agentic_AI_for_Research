"""Unified cache for embeddings, searches, validations, and LLM responses."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import configure_logging, ensure_dirs

configure_logging()
logger = logging.getLogger(__name__)

CACHE_DIR = Path(".data/cache")
ensure_dirs(CACHE_DIR)

EMBEDDING_CACHE_FILE = CACHE_DIR / "embeddings.json"
SEARCH_CACHE_FILE = CACHE_DIR / "searches.json"
VALIDATION_CACHE_FILE = CACHE_DIR / "validations.json"
LLM_CACHE_FILE = CACHE_DIR / "llm_responses.json"

_CACHES: Dict[str, Optional[Dict[str, Any]]] = {
    "embeddings": None,
    "searches": None,
    "validations": None,
    "llm": None,
}


def _load_cache(cache_type: str) -> Dict[str, Any]:
    global _CACHES
    if _CACHES[cache_type] is None:
        cache_files = {
            "embeddings": EMBEDDING_CACHE_FILE,
            "searches": SEARCH_CACHE_FILE,
            "validations": VALIDATION_CACHE_FILE,
            "llm": LLM_CACHE_FILE,
        }
        cache_file = cache_files.get(cache_type)
        if cache_file and cache_file.exists():
            try:
                _CACHES[cache_type] = json.loads(cache_file.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                _CACHES[cache_type] = {}
        else:
            _CACHES[cache_type] = {}
    return _CACHES[cache_type]


def _save_cache(cache_type: str) -> None:
    cache_files = {
        "embeddings": EMBEDDING_CACHE_FILE,
        "searches": SEARCH_CACHE_FILE,
        "validations": VALIDATION_CACHE_FILE,
        "llm": LLM_CACHE_FILE,
    }
    cache_file = cache_files.get(cache_type)
    if cache_file:
        data = _CACHES.get(cache_type, {})
        cache_file.write_text(json.dumps(data, indent=2), encoding="utf-8")


def cache_get(key: str, cache_type: str = "validations") -> Optional[Any]:
    data = _load_cache(cache_type)
    return data.get(key)


def cache_set(key: str, value: Any, cache_type: str = "validations") -> None:
    data = _load_cache(cache_type)
    data[key] = value
    _CACHES[cache_type] = data
    _save_cache(cache_type)
    logger.debug("Cached %s entry: %s", cache_type, key[:16])


def embedding_cache_get(key: str) -> Optional[list[float]]:
    return cache_get(key, cache_type="embeddings")


def embedding_cache_set(key: str, value: list[float]) -> None:
    cache_set(key, value, cache_type="embeddings")


def search_cache_get(key: str) -> Optional[Dict[str, Any]]:
    return cache_get(key, cache_type="searches")


def search_cache_set(key: str, value: Dict[str, Any]) -> None:
    cache_set(key, value, cache_type="searches")


def llm_cache_get(key: str) -> Optional[str]:
    return cache_get(key, cache_type="llm")


def llm_cache_set(key: str, value: str) -> None:
    cache_set(key, value, cache_type="llm")


def get_cache_stats() -> Dict[str, int]:
    return {
        "embeddings": len(_load_cache("embeddings")),
        "searches": len(_load_cache("searches")),
        "validations": len(_load_cache("validations")),
        "llm": len(_load_cache("llm")),
    }


def clear_cache(cache_type: Optional[str] = None) -> None:
    if cache_type:
        _CACHES[cache_type] = {}
        _save_cache(cache_type)
        logger.info("Cleared %s cache", cache_type)
    else:
        for ctype in _CACHES.keys():
            _CACHES[ctype] = {}
            _save_cache(ctype)
        logger.info("Cleared all caches")
