"""Evidence validation utilities."""

from __future__ import annotations

import hashlib
import re
from typing import Dict, Tuple

from .cache import cache_get, cache_set
from .llm import call_llm_json
from .schemas import Claim, EvidenceSpan
from .storage import load_page_text

_NORMALIZE_PATTERN = re.compile(r"\s+")


def _normalize(text: str) -> str:
    return _NORMALIZE_PATTERN.sub(" ", text).strip()


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
    context = _span_context(span, window)
    quote_norm = _normalize(span.quote).lower()
    snippet_norm = _normalize(context).lower()
    if not quote_norm:
        return False, "Quote text is empty"
    if quote_norm in snippet_norm:
        return True, "Quote found in cited window"
    return False, "Quote not found near cited span"


def _extract_keywords(text: str) -> list[str]:
    tokens = re.findall(r"\b\w{3,}\b", text.lower())
    return [t for t in tokens if t not in {"the", "and", "for", "are", "was", "that", "with", "from", "this"}]


def _level_1_structural_validation(span: EvidenceSpan) -> Dict[str, str | float | bool]:
    if not span.quote or not span.quote.strip():
        return {"level": 1, "confidence": 0.0, "verdict": "Weak", "reason": "Empty quote"}

    if span.page < 1:
        return {"level": 1, "confidence": 0.0, "verdict": "Weak", "reason": "Invalid page number"}

    if span.char_start < 0 or span.char_end < span.char_start:
        return {"level": 1, "confidence": 0.0, "verdict": "Weak", "reason": "Invalid character range"}

    ok, msg = verify_span(span)
    if ok:
        return {"level": 1, "confidence": 0.95, "verdict": "Supported", "reason": msg}

    return {"level": 1, "confidence": 0.4, "verdict": "Weak", "reason": msg}


def _level_2_keyword_analysis(claim_text: str, span: EvidenceSpan) -> Dict[str, str | float]:
    context = _span_context(span)
    if not context:
        return {"level": 2, "confidence": 0.0, "verdict": "Weak", "reason": "No context available"}

    claim_keywords = _extract_keywords(claim_text)
    context_keywords = _extract_keywords(context)
    if not claim_keywords:
        return {"level": 2, "confidence": 0.5, "verdict": "Weak", "reason": "No keywords in claim"}

    matched = sum(1 for kw in claim_keywords if kw in context_keywords)
    keyword_ratio = matched / len(claim_keywords)

    if keyword_ratio >= 0.8:
        return {"level": 2, "confidence": 0.85, "verdict": "Supported", "reason": f"High keyword match: {keyword_ratio:.1%}"}
    elif keyword_ratio >= 0.5:
        return {"level": 2, "confidence": 0.6, "verdict": "Weak", "reason": f"Medium keyword match: {keyword_ratio:.1%}"}
    else:
        return {"level": 2, "confidence": 0.3, "verdict": "Contradicted", "reason": f"Low keyword match: {keyword_ratio:.1%}"}


def _level_3_semantic_validation(claim_text: str, span: EvidenceSpan) -> Dict[str, str | float]:
    evidence = _span_context(span)
    if not evidence:
        return {"level": 3, "confidence": 0.0, "verdict": "Weak", "reason": "No evidence text available"}

    key_raw = f"{claim_text}|{span.source_id}|{span.page}|{evidence}"
    cache_key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()
    cached = cache_get(cache_key)
    if cached:
        cached["level"] = 3
        return cached

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
        verdict = str(payload.get("verdict", "Weak")).capitalize()
        if verdict not in {"Supported", "Weak", "Contradicted"}:
            verdict = "Weak"
        notes = payload.get("notes") or payload.get("explanation") or "No rationale provided."
        notes = notes.strip()

        cached_result = {"verdict": verdict, "notes": notes}
        cache_set(cache_key, cached_result)

        return {
            "level": 3,
            "confidence": 0.9,
            "verdict": verdict,
            "reason": notes,
        }
    except Exception as exc:
        return {"level": 3, "confidence": 0.0, "verdict": "Weak", "reason": f"LLM call failed: {exc}"}


def verify_span_multilevel(claim_text: str, span: EvidenceSpan) -> Dict[str, str | float]:
    level1 = _level_1_structural_validation(span)
    if level1["confidence"] >= 0.9:
        return level1

    level2 = _level_2_keyword_analysis(claim_text, span)
    if level2["verdict"] == "Supported" and level2["confidence"] >= 0.8:
        return level2
    if level2["verdict"] == "Contradicted":
        return level2

    return _level_3_semantic_validation(claim_text, span)


def assess_span_support(claim_text: str, span: EvidenceSpan) -> Tuple[str, str]:
    result = verify_span_multilevel(claim_text, span)
    verdict = result.get("verdict", "Weak")
    reason = result.get("reason", "Unknown validation error")
    level = result.get("level", 0)
    return verdict, f"[Level {level}] {reason}"
