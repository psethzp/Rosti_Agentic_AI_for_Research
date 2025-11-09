"""Agent orchestration utilities."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence, Tuple

from .reporting import render_report_html
from .retrieval import search
from .schemas import Claim, EvidenceSpan, Insight, ReviewedClaim
from .utils import configure_logging, ensure_dirs
from .validator import assess_span_support

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


def load_claims_from_artifacts() -> List[Claim]:
    path = _artifacts_dir() / "claims.json"
    if not path.exists():
        raise FileNotFoundError("claims.json not found. Run the researcher stage first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Claim.model_validate(entry) for entry in data]


def _persist_reviewed_claims(claims: Iterable[ReviewedClaim]) -> None:
    path = _artifacts_dir() / "claims_reviewed.json"
    payload = [claim.model_dump() for claim in claims]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Wrote %d reviewed claims to %s", len(payload), path)


def _persist_report(insights: List[Insight], claims: List[ReviewedClaim]) -> None:
    json_path = _artifacts_dir() / "report.json"
    html_path = _artifacts_dir() / "report.html"
    json_path.write_text(
        json.dumps([insight.model_dump() for insight in insights], indent=2),
        encoding="utf-8",
    )
    html = render_report_html(insights, claims)
    html_path.write_text(html, encoding="utf-8")
    logger.info("Wrote report artifacts to %s and %s", json_path, html_path)


def reset_artifacts(include_claims: bool = False) -> None:
    artifacts_path = _artifacts_dir()
    for path in (
        artifacts_path / "claims_reviewed.json",
        artifacts_path / "report.json",
        artifacts_path / "report.html",
    ):
        if path.exists():
            path.unlink()
            logger.info("Removed artifact %s", path)
    if include_claims:
        path = artifacts_path / "claims.json"
        if path.exists():
            path.unlink()
            logger.info("Removed artifact %s", path)


def run_researcher(topic: str) -> List[Claim]:
    if not topic.strip():
        raise ValueError("Topic must not be empty")

    reset_artifacts(include_claims=False)

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
    reviewed: List[ReviewedClaim] = []
    for claim in claims:
        base = claim.model_dump()
        base["status"] = "reviewed"
        if not claim.citations:
            reviewed.append(
                ReviewedClaim(
                    **base,
                    verdict="Weak",
                    reviewer_notes="Missing citations",
                )
            )
            continue

        results = [assess_span_support(claim.text, span) for span in claim.citations]
        verdicts = [verdict for verdict, _ in results]

        if all(v == "Supported" for v in verdicts):
            final_verdict = "Supported"
            notes = "All citations verified"
        elif any(v == "Contradicted" for v in verdicts):
            final_verdict = "Contradicted"
            idx = next(i for i, v in enumerate(verdicts) if v == "Contradicted")
            notes = results[idx][1]
        elif any(v == "Supported" for v in verdicts):
            final_verdict = "Weak"
            idx = next(i for i, v in enumerate(verdicts) if v == "Weak")
            notes = results[idx][1] if idx < len(results) else "Some citations weak"
        else:
            final_verdict = "Weak"
            notes = results[0][1] if results else "Validation inconclusive"

        reviewed.append(
            ReviewedClaim(
                **base,
                verdict=final_verdict,
                reviewer_notes=notes,
            )
        )

    _persist_reviewed_claims(reviewed)
    return reviewed


def run_synthesizer(topic: str, reviewed: List[ReviewedClaim]) -> List[Insight]:
    supported = [claim for claim in reviewed if claim.verdict == "Supported"]
    weak = [claim for claim in reviewed if claim.verdict == "Weak"]
    if not supported and not weak:
        logger.warning("No reviewed claims available to synthesize insights.")
        _persist_report([], reviewed)
        return []

    selected_claims = supported or weak[:3]
    insights: List[Insight] = []
    chunk_size = max(1, len(selected_claims) // 3 + (1 if len(selected_claims) > 3 else 0))
    for idx in range(0, len(selected_claims), chunk_size):
        group = selected_claims[idx : idx + chunk_size]
        text = " ".join(claim.text for claim in group)
        claim_ids = [claim.id for claim in group]
        provenance = [span for claim in group for span in claim.citations]
        insight = Insight(
            id=f"i{len(insights) + 1:04d}",
            topic=topic,
            claim_ids=claim_ids,
            text=text,
            confidence=min(0.95, sum((claim.confidence or 0.6) for claim in group) / len(group)),
            provenance=provenance,
        )
        insights.append(insight)
        if len(insights) >= 5:
            break

    _persist_report(insights, reviewed)
    return insights
