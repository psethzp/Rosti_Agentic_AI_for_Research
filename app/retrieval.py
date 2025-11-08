"""Hybrid retrieval helpers for claims generation."""

from __future__ import annotations

import logging
import re
from typing import Dict, List

from .utils import configure_logging
from .vectorstore import build_embeddings, get_collection

configure_logging()
logger = logging.getLogger(__name__)


def _format_results(response: Dict) -> List[Dict]:
    documents = response.get("documents") or [[]]
    metadatas = response.get("metadatas") or [[]]
    ids = response.get("ids") or [[]]
    distances = response.get("distances") or [[]]

    docs = documents[0] if documents else []
    metas = metadatas[0] if metadatas else []
    result_ids = ids[0] if ids else []
    dist = distances[0] if distances else []

    results: List[Dict] = []
    for idx, text in enumerate(docs):
        meta = metas[idx] if idx < len(metas) else {}
        chunk_id = result_ids[idx] if idx < len(result_ids) else f"chunk-{idx}"
        distance = dist[idx] if idx < len(dist) else None
        score = 1.0 / (1.0 + distance) if distance is not None else 0.0
        results.append(
            {
                "id": chunk_id,
                "text": text or "",
                "score": score,
                "source_id": meta.get("source_id"),
                "page": meta.get("page"),
                "char_start": meta.get("char_start", 0),
                "char_end": meta.get("char_end", 0),
            }
        )
    return results


def _keyword_fallback(query: str, k: int = 6) -> List[Dict]:
    collection = get_collection()
    raw = collection.get(include=["documents", "metadatas", "ids"])
    docs = raw.get("documents", [])
    metas = raw.get("metadatas", [])
    ids = raw.get("ids", [])
    terms = [t.lower() for t in re.findall(r"\w+", query)]
    scores: List[Dict] = []
    for text, meta, chunk_id in zip(docs, metas, ids):
        lowered = text.lower()
        match_score = sum(lowered.count(term) for term in terms) if terms else 0
        if match_score <= 0:
            continue
        scores.append(
            {
                "id": chunk_id,
                "text": text,
                "score": float(match_score),
                "source_id": meta.get("source_id"),
                "page": meta.get("page"),
                "char_start": meta.get("char_start", 0),
                "char_end": meta.get("char_end", 0),
            }
        )
    scores.sort(key=lambda item: (-item["score"], item["id"]))
    return scores[:k]


def search(query: str, k: int = 6) -> List[Dict]:
    """Return ranked chunk metadata for a query."""
    if not query.strip():
        raise ValueError("Query must be non-empty")

    collection = get_collection()
    embeddings = build_embeddings([query])
    try:
        response = collection.query(query_embeddings=embeddings, n_results=k)
        results = _format_results(response)
        if results:
            results.sort(key=lambda item: (-item["score"], item["id"]))
            return results[:k]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Dense retrieval failed (%s); falling back to keyword search", exc)

    fallback_results = _keyword_fallback(query, k)
    if not fallback_results:
        logger.info("No results found for query '%s'", query)
    return fallback_results
