"""Agent orchestration utilities."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, Tuple

from .retrieval import search
from .schemas import Claim, EvidenceSpan, Insight, ReviewedClaim
from .utils import configure_logging, ensure_dirs

configure_logging()
logger = logging.getLogger(__name__)

MIN_CLAIMS = 3
MAX_CLAIMS = 7


def _artifacts_dir() -> Path:
    path = Path(os.getenv("ARTIFACTS_DIR", "artifacts")).expanduser()
    ensure_dirs(path)
    return path


def _normalize_text(text: str) -> str:
    """Collapse whitespace and strip surrounding spaces."""
    return re.sub(r"\s+", " ", text.strip())


def _sentence_chunks(text: str) -> List[str]:
    normalized = _normalize_text(text)
    if not normalized:
        return []
    parts = re.split(r"(?<=[.!?])\s+", normalized)
    sentences = [part for part in parts if part]
    return sentences or [normalized]


def _yield_sentences(results: Sequence[dict]) -> Iterator[Tuple[str, dict, int]]:
    for hit in results:
        chunk_text = hit.get("text", "")
        sentences = _sentence_chunks(chunk_text)
        for sentence in sentences:
            relative_idx = chunk_text.find(sentence)
            yield sentence, hit, relative_idx


def _clip_quote(text: str, limit: int = 320) -> str:
    normalized = _normalize_text(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _make_evidence_span(hit: dict, sentence: str, relative_idx: int) -> EvidenceSpan:
    base_start = hit.get("char_start", 0)
    if relative_idx >= 0:
        char_start = base_start + relative_idx
    else:
        char_start = base_start
    char_end = char_start + len(sentence)
    return EvidenceSpan(
        source_id=hit.get("source_id", "unknown"),
        page=hit.get("page", 1),
        char_start=char_start,
        char_end=char_end,
        quote=_clip_quote(sentence),
    )


def _persist_claims(claims: Iterable[Claim]) -> None:
    path = _artifacts_dir() / "claims.json"
    payload = [claim.model_dump() for claim in claims]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Wrote %d claims to %s", len(payload), path)


def run_researcher(topic: str) -> List[Claim]:
    """Generate claims for a topic using retrieval results."""
    if not topic.strip():
        raise ValueError("Topic must not be empty")

    hits = search(topic, k=MAX_CLAIMS * 2)
    if not hits:
        raise RuntimeError("No retrieval results available. Ingest documents first.")

    claims: List[Claim] = []
    for idx, (sentence, hit, rel_idx) in enumerate(_yield_sentences(hits)):
        claim_id = f"c{idx + 1:04d}"
        span = _make_evidence_span(hit, sentence, rel_idx)
        text = sentence if sentence.endswith(".") else f"{sentence}."
        claims.append(
            Claim(
                id=claim_id,
                topic=topic,
                text=text,
                citations=[span],
                confidence=0.65,
                status="draft",
            )
        )
        if len(claims) >= MAX_CLAIMS:
            break

    if len(claims) < MIN_CLAIMS and hits:
        logger.warning(
            "Only %d claims generated; reusing sentences to reach %d",
            len(claims),
            MIN_CLAIMS,
        )
        idx = 0
        while len(claims) < MIN_CLAIMS:
            hit = hits[idx % len(hits)]
            sentence = _sentence_chunks(hit.get("text", ""))[0]
            span = _make_evidence_span(hit, sentence, hit.get("text", "").find(sentence))
            claims.append(
                Claim(
                    id=f"c{len(claims) + 1:04d}",
                    topic=topic,
                    text=sentence if sentence.endswith(".") else f"{sentence}.",
                    citations=[span],
                    confidence=0.5,
                    status="draft",
                )
            )
            idx += 1

    _persist_claims(claims)
    return claims


def run_reviewer(claims: List[Claim]) -> List[ReviewedClaim]:
    """Review claims and assign verdicts."""
    raise NotImplementedError


def run_synthesizer(topic: str, reviewed: List[ReviewedClaim]) -> List[Insight]:
    """Synthesize reviewed claims into final insights."""
    raise NotImplementedError
