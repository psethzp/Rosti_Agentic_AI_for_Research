"""Reporting/export helpers."""

from __future__ import annotations

import html
from pathlib import Path
from typing import Iterable, List

from .schemas import ActionItem, Insight, ReviewedClaim

TEMPLATE_PATH = Path("assets/report_template.html")


def _render_claims_table(claims: Iterable[ReviewedClaim]) -> str:
    rows = []
    for claim in claims:
        citation = claim.citations[0] if claim.citations else None
        location = (
            f"{citation.source_id} p{citation.page}" if citation else "N/A"
        )
        rows.append(
            "<tr>"
            f"<td>{html.escape(claim.id)}</td>"
            f"<td>{html.escape(claim.text)}</td>"
            f"<td>{html.escape(claim.verdict)}</td>"
            f"<td>{html.escape(claim.reviewer_notes)}</td>"
            f"<td>{html.escape(location)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _render_insight_cards(insights: Iterable[Insight]) -> str:
    cards = []
    for insight in insights:
        citations = ", ".join(
            f"{span.source_id} p{span.page}" for span in insight.provenance
        )
        cards.append(
            "<section class='insight'>"
            f"<h3>{html.escape(insight.id)} · Confidence {insight.confidence:.2f}</h3>"
            f"<p><strong>Summary:</strong> {html.escape(insight.summary)}</p>"
            f"<p>{html.escape(insight.text)}</p>"
            f"<p class='provenance'><strong>Provenance:</strong> {html.escape(citations)}</p>"
            "</section>"
        )
    return "\n".join(cards)


def _render_actions(actions: Iterable[ActionItem]) -> str:
    sections = []
    for action in actions:
        sections.append(
            "<section class='action'>"
            f"<h4>{html.escape(action.title)} · {html.escape(action.tag)}</h4>"
            f"<p>{html.escape(action.detail)}</p>"
            "</section>"
        )
    return "\n".join(sections)


def render_report_html(
    insights: List[Insight],
    claims: List[ReviewedClaim],
    actions: List[ActionItem],
) -> str:
    """Render a simple HTML report using the template."""
    template = TEMPLATE_PATH.read_text(encoding="utf-8")
    rendered = template.format(
        insight_cards=_render_insight_cards(insights),
        claims_table=_render_claims_table(claims),
        actions_section=_render_actions(actions),
    )
    return rendered
