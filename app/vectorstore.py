"""Shared helpers for interacting with the Chroma vector store."""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
from pathlib import Path
from typing import Iterable, List, Optional

os.environ.setdefault("CHROMA_TELEMETRY", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

import chromadb
from chromadb.api import Collection
from chromadb.config import Settings
from chromadb.errors import InvalidDimensionException

try:
    from chromadb.telemetry.product import posthog as chroma_posthog

    def _noop_capture(*args, **kwargs) -> None:  # type: ignore[override]
        return None

    chroma_posthog.Posthog.capture = _noop_capture  # type: ignore[assignment]
except Exception:
    pass

from .utils import configure_logging, ensure_dirs

configure_logging()
logger = logging.getLogger(__name__)


_env_cache: dict[str, Optional[str]] = {}


def _env(key: str, default: Optional[str] = None) -> Optional[str]:
    if key not in _env_cache:
        _env_cache[key] = os.getenv(key, default)
    return _env_cache[key]


def get_chroma_dir() -> Path:
    """Return the configured Chroma directory."""
    return Path(_env("CHROMA_DIR", ".data/chroma") or ".data/chroma").expanduser()


def get_collection_name() -> str:
    """Return the Chroma collection name."""
    return _env("CHROMA_COLLECTION", "docs") or "docs"


def get_collection() -> Collection:
    """Create or retrieve the configured Chroma collection."""
    chroma_dir = get_chroma_dir()
    ensure_dirs(chroma_dir)
    try:
        client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(name=get_collection_name())
        return collection
    except ValueError:
        logger.warning("Chroma tenant missing; resetting vector store.")
        reset_vector_store()
        client = chromadb.PersistentClient(
            path=str(chroma_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(name=get_collection_name())
        return collection


def reset_vector_store() -> None:
    """Delete the current Chroma directory to reset embeddings."""
    chroma_dir = get_chroma_dir()
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)
    ensure_dirs(chroma_dir)


def _hash_to_embedding(text: str, dim: int = 32) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    if len(digest) < dim:
        digest = (digest * (dim // len(digest) + 1))[:dim]
    return [b / 255.0 for b in digest[:dim]]


def build_embeddings(texts: Iterable[str]) -> List[List[float]]:
    """Return embeddings for the provided texts via Gemini."""
    texts = list(texts)
    if not texts:
        return []

    gemini_key = _env("GEMINI_API_KEY")
    gemini_model = _env("EMBED_MODEL_GEMINI", "models/embedding-001") or "models/embedding-001"
    if gemini_model and not gemini_model.startswith(("models/", "tunedModels/")):
        gemini_model = f"models/{gemini_model}"
    if not gemini_key:
        raise RuntimeError("GEMINI_API_KEY is required for embeddings.")
    try:
        import google.generativeai as genai

        genai.configure(api_key=gemini_key)
        embeddings: List[List[float]] = []
        for text in texts:
            response = genai.embed_content(model=gemini_model, content=text)
            embeddings.append(response["embedding"])
        logger.info(
            "Generated %d embeddings via Gemini %s (dimension %d)",
            len(embeddings),
            gemini_model,
            len(embeddings[0]) if embeddings else 0,
        )
        return embeddings
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Gemini embeddings failed: {exc}") from exc
