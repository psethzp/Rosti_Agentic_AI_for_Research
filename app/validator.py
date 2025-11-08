"""Evidence validation utilities."""

from __future__ import annotations

import hashlib
import re
from typing import Tuple

from .cache import cache_get, cache_set
from .llm import call_llm_json
from .schemas import EvidenceSpan
from .storage import load_page_text


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _span_context(span: EvidenceSpan, window: int = 280) -> str:
    if span.chunk_text:
        return span.chunk_text
    page_text = load_page_text(span.source_id, span.page)
    if not page_text:
        return span.quote
    start = max(span.char_start - window, 0)
    end = min(span.char_end + window, len(page_text))
    return page_text[start:end]


def verify_span(span: EvidenceSpan, window: int = 280) -> Tuple[bool, str]:
    """Legacy exact-match validator retained for fallback."""
    context = _span_context(span, window)
    quote_norm = _normalize(span.quote).lower()
    snippet_norm = _normalize(context).lower()
    if not quote_norm:
        return False, "Quote text is empty"
    if quote_norm in snippet_norm:
        return True, "Quote found in cited window"
    return False, "Quote not found near cited span"


def assess_span_support(claim_text: str, span: EvidenceSpan) -> Tuple[str, str]:
    """Use Gemini to judge whether evidence supports the claim."""
    evidence = _span_context(span)
    if not evidence:
        return "Weak", "No evidence text available."

    key_raw = f"{claim_text}|{span.source_id}|{span.page}|{evidence}"
    cache_key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()
    cached = cache_get(cache_key)
    if cached:
        return cached["verdict"], cached["notes"]

    system_prompt = (
        "You are a meticulous reviewer. Given a claim and an evidence excerpt, "
        "decide if the evidence Supports the claim, is Weakly related, or Contradicts it. "
        "Respond with JSON: {\"verdict\": \"Supported\"|\"Weak\"|\"Contradicted\", "
        "\"notes\": \"short explanation\"}."
    )
    user_prompt = f"Claim: {claim_text}\nEvidence excerpt: {evidence}"
    try:
        result = call_llm_json(system_prompt, user_prompt)
        payload = result[0] if isinstance(result, list) else result
    except Exception as exc:  # noqa: BLE001
        return "Weak", f"Semantic validation failed: {exc}"

    verdict = str(payload.get("verdict", "Weak")).capitalize()
    if verdict not in {"Supported", "Weak", "Contradicted"}:
        verdict = "Weak"
    notes = payload.get("notes") or payload.get("explanation") or "No rationale provided."
    notes = notes.strip()
    cache_set(cache_key, {"verdict": verdict, "notes": notes})
    return verdict, notes
