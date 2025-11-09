"""Shared helpers for interacting with the Chroma vector store."""

from __future__ import annotations

import hashlib
import logging
import os
from pathlib import Path
from typing import Iterable, List

os.environ.setdefault("CHROMA_TELEMETRY", "false")
os.environ.setdefault("ANONYMIZED_TELEMETRY", "false")

import chromadb
from chromadb.api import Collection
from chromadb.config import Settings

try:
    from chromadb.telemetry.product import posthog as chroma_posthog

    def _noop_capture(*args, **kwargs) -> None:
        return None

    chroma_posthog.Posthog.capture = _noop_capture
except Exception:
    pass

from .cache import embedding_cache_get, embedding_cache_set
from .utils import configure_logging, ensure_dirs

configure_logging()
logger = logging.getLogger(__name__)


def get_chroma_dir() -> Path:
    return Path(os.getenv("CHROMA_DIR", ".data/chroma")).expanduser()


def get_collection_name() -> str:
    return os.getenv("CHROMA_COLLECTION", "docs")


def get_collection() -> Collection:
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
    texts = list(texts)
    if not texts:
        return []

    cached_results = []
    uncached_texts = []
    uncached_indices = []

    for idx, text in enumerate(texts):
        cache_key = hashlib.sha256(text.encode("utf-8")).hexdigest()
        cached = embedding_cache_get(cache_key)
        if cached:
            cached_results.append((idx, cached))
        else:
            uncached_texts.append(text)
            uncached_indices.append((idx, cache_key))

    if uncached_texts:
        api_key = os.getenv("OPENAI_API_KEY")
        model = os.getenv("EMBED_MODEL", "text-embedding-large")
        if api_key:
            try:
                from openai import OpenAI

                client = OpenAI(api_key=api_key)
                response = client.embeddings.create(model=model, input=uncached_texts)
                embeddings = [item.embedding for item in response.data]
                for (idx, cache_key), embedding in zip(uncached_indices, embeddings):
                    embedding_cache_set(cache_key, embedding)
                    cached_results.append((idx, embedding))
                logger.info(
                    "Generated %d embeddings via %s (cached %d)",
                    len(embeddings),
                    model,
                    len(cached_results) - len(embeddings),
                )
            except Exception as exc:
                logger.warning("Falling back to deterministic embeddings: %s", exc)
                for (idx, cache_key), text in zip(uncached_indices, uncached_texts):
                    embedding = _hash_to_embedding(text)
                    embedding_cache_set(cache_key, embedding)
                    cached_results.append((idx, embedding))
        else:
            logger.debug("Using deterministic embeddings for %d texts", len(uncached_texts))
            for (idx, cache_key), text in zip(uncached_indices, uncached_texts):
                embedding = _hash_to_embedding(text)
                embedding_cache_set(cache_key, embedding)
                cached_results.append((idx, embedding))
    else:
        logger.info("All %d embeddings served from cache", len(texts))

    cached_results.sort(key=lambda x: x[0])
    return [embedding for _, embedding in cached_results]
