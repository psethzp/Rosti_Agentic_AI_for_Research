"""Reporting/export helpers placeholder."""

from __future__ import annotations

from typing import List

from .schemas import Insight, ReviewedClaim


def render_report_html(insights: List[Insight], claims: List[ReviewedClaim]) -> str:
    """Render report HTML string using insights and claims."""
    raise NotImplementedError
