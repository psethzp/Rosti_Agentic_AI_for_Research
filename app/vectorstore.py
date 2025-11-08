"""Shared helpers for interacting with the Chroma vector store."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Iterable, List

import os

os.environ.setdefault("CHROMA_TELEMETRY", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

import chromadb
from chromadb.api import Collection
from chromadb.config import Settings

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


def get_chroma_dir() -> Path:
    """Return the configured Chroma directory."""
    return Path(os.getenv("CHROMA_DIR", ".data/chroma")).expanduser()


def get_collection_name() -> str:
    """Return the Chroma collection name."""
    return os.getenv("CHROMA_COLLECTION", "docs")


def get_collection() -> Collection:
    """Create or retrieve the configured Chroma collection."""
    chroma_dir = get_chroma_dir()
    ensure_dirs(chroma_dir)
    client = chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection(name=get_collection_name())
    return collection


def _hash_to_embedding(text: str, dim: int = 32) -> List[float]:
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    if len(digest) < dim:
        digest = (digest * (dim // len(digest) + 1))[:dim]
    return [b / 255.0 for b in digest[:dim]]


def build_embeddings(texts: Iterable[str]) -> List[List[float]]:
    """Return embeddings for the provided texts via OpenAI or a deterministic fallback."""
    texts = list(texts)
    if not texts:
        return []

    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("EMBED_MODEL", "text-embedding-large")
    if api_key:
        try:
            from openai import OpenAI

            client = OpenAI(api_key=api_key)
            response = client.embeddings.create(model=model, input=texts)
            embeddings = [item.embedding for item in response.data]
            logger.info("Generated %d embeddings via %s", len(embeddings), model)
            return embeddings
        except Exception as exc:  # noqa: BLE001
            logger.warning("Falling back to deterministic embeddings: %s", exc)

    logger.debug("Using deterministic embeddings for %d texts", len(texts))
    return [_hash_to_embedding(text) for text in texts]
