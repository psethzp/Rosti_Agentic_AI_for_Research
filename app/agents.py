"""Agent orchestration placeholders."""

from __future__ import annotations

from typing import List

from .schemas import Claim, ReviewedClaim, Insight


def run_researcher(topic: str) -> List[Claim]:
    """Generate claims for a topic using retrieval-backed LLM."""
    raise NotImplementedError


def run_reviewer(claims: List[Claim]) -> List[ReviewedClaim]:
    """Review claims and assign verdicts."""
    raise NotImplementedError


def run_synthesizer(topic: str, reviewed: List[ReviewedClaim]) -> List[Insight]:
    """Synthesize reviewed claims into final insights."""
    raise NotImplementedError
