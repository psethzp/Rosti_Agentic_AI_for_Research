"""Evidence validation utilities."""

from __future__ import annotations

import re
from typing import Tuple

from .schemas import EvidenceSpan
from .storage import load_page_text


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def verify_span(span: EvidenceSpan, window: int = 280) -> Tuple[bool, str]:
    """Verify that a quote exists near the cited span."""
    page_text = load_page_text(span.source_id, span.page)
    if page_text is None:
        return False, f"No cached text for {span.source_id} p{span.page}"

    start = max(span.char_start - window, 0)
    end = min(span.char_end + window, len(page_text))
    snippet = page_text[start:end]
    quote_norm = _normalize(span.quote)
    snippet_norm = _normalize(snippet)
    if not quote_norm:
        return False, "Quote text is empty"

    if quote_norm in snippet_norm:
        return True, "Quote found in cited window"
    return False, "Quote not found near cited span"
