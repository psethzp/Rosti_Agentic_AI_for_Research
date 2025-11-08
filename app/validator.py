"""Evidence validation utilities."""

from __future__ import annotations

from typing import Tuple

from .schemas import EvidenceSpan


def verify_span(span: EvidenceSpan, window: int = 280) -> Tuple[bool, str]:
    """Verify that a quote exists near the cited span."""
    raise NotImplementedError
