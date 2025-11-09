"""Agent orchestration utilities."""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Iterable, Iterator, List, Optional, Sequence, Tuple

from .llm import call_llm_json
from .reporting import render_report_html
from .retrieval import search
from .schemas import ActionItem, Claim, EvidenceSpan, Insight, RedTeamFinding, ReviewedClaim
from .utils import configure_logging, ensure_dirs
from .validator import assess_span_support, verify_span

configure_logging()
logger = logging.getLogger(__name__)

MIN_CLAIMS = 3
MAX_CLAIMS = 5


def _artifacts_dir() -> Path:
    path = Path(os.getenv("ARTIFACTS_DIR", "artifacts")).expanduser()
    ensure_dirs(path)
    return path


def _claims_path() -> Path:
    return _artifacts_dir() / "claims.json"


def _claims_reviewed_path() -> Path:
    return _artifacts_dir() / "claims_reviewed.json"


def _report_json_path() -> Path:
    return _artifacts_dir() / "report.json"


def _report_html_path() -> Path:
    return _artifacts_dir() / "report.html"


def _actions_path() -> Path:
    return _artifacts_dir() / "actions.json"


def _challenges_path() -> Path:
    return _artifacts_dir() / "challenges.json"


def reset_artifacts(include_claims: bool = False) -> None:
    """Remove downstream artifact files to avoid stale UI state."""
    for path in (
        _claims_reviewed_path(),
        _report_json_path(),
        _report_html_path(),
        _actions_path(),
        _challenges_path(),
    ):
        if path.exists():
            path.unlink()
            logger.info("Removed artifact %s", path)
    if include_claims:
        path = _claims_path()
        if path.exists():
            path.unlink()
            logger.info("Removed artifact %s", path)


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
        chunk_id=hit.get("id"),
        chunk_text=hit.get("text"),
    )


def _persist_claims(claims: Iterable[Claim]) -> None:
    path = _claims_path()
    payload = [claim.model_dump() for claim in claims]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Wrote %d claims to %s", len(payload), path)


def load_claims_from_artifacts() -> List[Claim]:
    path = _claims_path()
    if not path.exists():
        raise FileNotFoundError("claims.json not found. Run the researcher stage first.")
    data = json.loads(path.read_text(encoding="utf-8"))
    return [Claim.model_validate(entry) for entry in data]


def load_insights_from_artifacts() -> List[Insight]:
    path = _report_json_path()
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        raw_insights = data
    else:
        raw_insights = data.get("insights", [])
    return [Insight.model_validate(entry) for entry in raw_insights]


def _load_actions_from_artifacts() -> List[ActionItem]:
    path = _actions_path()
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ActionItem.model_validate(entry) for entry in data]


def _load_challenges_from_artifacts() -> List[RedTeamFinding]:
    path = _challenges_path()
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [RedTeamFinding.model_validate(entry) for entry in data]


def _persist_reviewed_claims(claims: Iterable[ReviewedClaim]) -> None:
    path = _claims_reviewed_path()
    payload = [claim.model_dump() for claim in claims]
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    logger.info("Wrote %d reviewed claims to %s", len(payload), path)


def _actions_path() -> Path:
    return _artifacts_dir() / "actions.json"


def _persist_report(
    insights: List[Insight],
    claims: List[ReviewedClaim],
    actions: Optional[List[ActionItem]] = None,
    challenges: Optional[List[RedTeamFinding]] = None,
) -> None:
    json_path = _report_json_path()
    html_path = _report_html_path()
    payload = {
        "insights": [insight.model_dump() for insight in insights],
        "actions": [action.model_dump() for action in (actions or [])],
        "challenges": [challenge.model_dump() for challenge in (challenges or [])],
    }
    json_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    html = render_report_html(insights, claims, actions or [], challenges or [])
    html_path.write_text(html, encoding="utf-8")
    logger.info("Wrote report artifacts to %s and %s", json_path, html_path)


def _persist_actions(actions: List[ActionItem]) -> None:
    path = _actions_path()
    path.write_text(
        json.dumps([action.model_dump() for action in actions], indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote %d action items to %s", len(actions), path)


def _persist_challenges(challenges: List[RedTeamFinding]) -> None:
    path = _challenges_path()
    path.write_text(
        json.dumps([challenge.model_dump() for challenge in challenges], indent=2),
        encoding="utf-8",
    )
    logger.info("Wrote %d red-team findings to %s", len(challenges), path)


def run_researcher(topic: str) -> List[Claim]:
    """Generate claims for a topic using retrieval results."""
    if not topic.strip():
        raise ValueError("Topic must not be empty")

    reset_artifacts(include_claims=False)

    hits = search(topic, k=MAX_CLAIMS * 4)
    if not hits:
        raise RuntimeError("No retrieval results available. Ingest documents first.")

    claims = _llm_researcher(topic, hits)
    if len(claims) < MIN_CLAIMS:
        logger.warning("LLM provided %d claims; using fallback extraction.", len(claims))
        claims = _fallback_claims(topic, hits)
    _persist_claims(claims)
    return claims


def run_reviewer(claims: List[Claim]) -> List[ReviewedClaim]:
    """Review claims and assign verdicts."""
    reviewed = []
    for claim in claims:
        base = claim.model_dump()
        base["status"] = "reviewed"
        reviewed.append(
            ReviewedClaim(
                **base,
                verdict="Supported",
                reviewer_notes="Auto-approved (review disabled).",
            )
        )
    _persist_reviewed_claims(reviewed)
    return reviewed


def run_synthesizer(
    topic: str,
    reviewed: List[ReviewedClaim],
    challenges: Optional[List[RedTeamFinding]] = None,
) -> List[Insight]:
    """Synthesize reviewed claims into final insights."""
    insights = _llm_synthesizer(topic, reviewed, challenges or _load_challenges_from_artifacts())
    if not insights:
        logger.warning("No insights synthesized; falling back to deterministic grouping.")
        insights = _fallback_insights(topic, reviewed)
    existing_actions = _load_actions_from_artifacts()
    _persist_report(
        insights,
        reviewed,
        existing_actions,
        challenges or _load_challenges_from_artifacts(),
    )
    return insights


def run_action_planner(
    topic: str,
    reviewed: List[ReviewedClaim],
    insights: Optional[List[Insight]] = None,
) -> List[ActionItem]:
    if not reviewed:
        raise ValueError("No reviewed claims available. Run reviewer first.")
    if insights is None:
        insights = load_insights_from_artifacts()

    insight_lines = [
        f"{insight.id}: {insight.summary} (claims: {', '.join(insight.claim_ids)})"
        for insight in insights
    ]
    claim_lines = [
        f"{claim.id} ({claim.verdict}): {claim.text}" for claim in reviewed
    ]
    challenge_lines = [
        f"{challenge.claim_id}: {challenge.summary}"
        for challenge in _load_challenges_from_artifacts()
    ]
    system_prompt = (
        "You are a strategic planner. Using the reviewed claims, synthesized insights, and red-team challenges, "
        "propose 3-5 forward-looking actions (mix of hypotheses, next steps, clarifications). "
        "Each action should directly address a gap or extend a finding, and cite relevant claim IDs. "
        "Output JSON list with objects {\"title\": \"...\", \"detail\": \"...\", "
        "\"tag\": \"Hypothesis\"|\"NextStep\"|\"Clarification\", "
        "\"related_claims\": [\"c0001\", ...] }."
    )
    user_prompt = (
        f"Topic: {topic}\nReviewed claims:\n"
        + "\n".join(claim_lines)
        + "\n\nInsights:\n"
        + ("\n".join(insight_lines) if insight_lines else "None yet.")
        + ("\n\nChallenges:\n" + "\n".join(challenge_lines) if challenge_lines else "")
    )
    try:
        llm_output = call_llm_json(system_prompt, user_prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Action planner LLM failed: %s", exc)
        return []

    actions: List[ActionItem] = []
    allowed_tags = {"Hypothesis", "NextStep", "Clarification"}
    for entry in llm_output:
        title = _normalize_text(entry.get("title", ""))
        detail = _normalize_text(entry.get("detail", entry.get("description", "")))
        if not title or not detail:
            continue
        tag = str(entry.get("tag", "NextStep")).title()
        if tag not in allowed_tags:
            tag = "NextStep"
        related = [
            cid for cid in entry.get("related_claims", []) if any(c.id == cid for c in reviewed)
        ]
        actions.append(
            ActionItem(
                id=f"a{len(actions) + 1:04d}",
                topic=topic,
                title=title,
                detail=detail if detail.endswith(".") else f"{detail}.",
                tag=tag, 
                related_claims=related,
            )
        )
        if len(actions) >= 5:
            break

    if actions:
        _persist_actions(actions)
        _persist_report(insights or [], reviewed, actions, _load_challenges_from_artifacts())
    else:
        logger.warning("No action items generated; retaining previous suggestions.")
    return actions


def run_red_team(
    topic: str,
    reviewed: List[ReviewedClaim],
    max_per_claim: int = 2,
    max_total: int = 5,
) -> List[RedTeamFinding]:
    candidates = [claim for claim in reviewed if claim.verdict in {"Supported", "Weak"}]
    findings: List[RedTeamFinding] = []
    for claim in candidates:
        evidence_hits = _gather_counter_evidence(claim)
        if not evidence_hits:
            continue
        system_prompt = (
            "You are Red Team. Given a claim and independent evidence snippets, "
            "identify the most significant contradictions, limitations, or unanswered questions. "
            "Output JSON list where each object has fields: "
            "{\"summary\": \"short sentence\", "
            "\"detail\": \"multi-sentence explanation\", "
            "\"severity\": \"High\"|\"Medium\"|\"Low\", "
            "\"evidence_refs\": [\"E1\"...], "
            "\"actions\": [\"bullet\", ...] }. "
            f"Return at most {max_per_claim} items ranked by importance."
        )
        evidence_lines = []
        evidence_map = {}
        for idx, hit in enumerate(evidence_hits):
            evid_id = f"E{idx + 1}"
            snippet = _normalize_text(hit.get("text", ""))[:800]
            evidence_lines.append(
                f"{evid_id}: Source={hit.get('source_id')} p{hit.get('page')} -> {snippet}"
            )
            evidence_map[evid_id] = hit
        user_prompt = (
            f"Topic: {topic}\nClaim ({claim.id}): {claim.text}\n\n"
            "Candidate evidence:\n" + "\n".join(evidence_lines)
        )
        try:
            llm_output = call_llm_json(system_prompt, user_prompt)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Red Team LLM failed for %s: %s", claim.id, exc)
            continue
        for entry in llm_output:
            summary = _normalize_text(entry.get("summary", ""))
            detail = _normalize_text(entry.get("detail", entry.get("text", "")))
            if not summary or not detail:
                continue
            evidence_refs = entry.get("evidence_refs", [])
            provenance: List[EvidenceSpan] = []
            for ref in evidence_refs:
                hit = evidence_map.get(ref)
                if not hit:
                    continue
                provenance.append(
                    EvidenceSpan(
                        source_id=hit.get("source_id", "unknown"),
                        page=hit.get("page", 1),
                        char_start=hit.get("char_start", 0),
                        char_end=hit.get("char_end", 0),
                        quote=_clip_quote(hit.get("text", "")),
                        chunk_id=hit.get("id"),
                        chunk_text=hit.get("text"),
                    )
                )
            if not provenance:
                continue
            severity = str(entry.get("severity", "Medium")).title()
            if severity not in {"High", "Medium", "Low"}:
                severity = "Medium"
            actions = entry.get("actions", [])
            detail_text = detail if detail.endswith(".") else f"{detail}."
            summary_text = summary if summary.endswith(".") else f"{summary}."
            findings.append(
                RedTeamFinding(
                    id=f"r{len(findings) + 1:04d}",
                    topic=topic,
                    claim_id=claim.id,
                    claim_text=claim.text,
                    summary=summary_text,
                    detail=detail_text,
                    evidence=provenance,
                    severity=severity,
                    actions=[_normalize_text(a) for a in actions if a],
                )
            )
    if findings:
        severity_rank = {"High": 0, "Medium": 1, "Low": 2}
        findings.sort(key=lambda f: severity_rank.get(f.severity, 1))
        findings = findings[:max_total]
    if findings:
        _persist_challenges(findings)
        _persist_report(
            load_insights_from_artifacts(),
            reviewed,
            _load_actions_from_artifacts(),
            findings,
        )
    else:
        logger.warning("Red Team found no contradictions.")
    return findings


def _llm_researcher(topic: str, hits: Sequence[dict]) -> List[Claim]:
    evidence_map = {}
    evidence_lines = []
    for idx, hit in enumerate(hits):
        evid_id = f"E{idx + 1}"
        snippet = _normalize_text(hit.get("text", ""))[:600]
        evidence_lines.append(
            f"{evid_id}: Source={hit.get('source_id')} page {hit.get('page')} -> {snippet}"
        )
        evidence_map[evid_id] = hit

    if not evidence_lines:
        return []

    system_prompt = (
        "You are Researcher. Read the evidence snippets and craft 3-5 master claims that synthesize them. "
        "For each claim, output JSON with keys: "
        "'summary' (single sentence headline), "
        "'subpoints' (array of 3-5 sentences, each grounded in the evidence), "
        "'evidence_refs' (list of evidence IDs cited across the subpoints), "
        "'confidence' (0-1). "
        "Make sure every subpoint references at least one evidence ID, and each claim draws from two or more evidence refs when possible. "
        "Use only the provided IDs (E1, E2, ...). Return a JSON list."
    )
    user_prompt = f"Topic: {topic}\nEvidence:\n" + "\n".join(evidence_lines)
    try:
        llm_output = call_llm_json(system_prompt, user_prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Researcher LLM failed: %s", exc)
        return []

    claims: List[Claim] = []
    for idx, entry in enumerate(llm_output):
        summary = _normalize_text(entry.get("summary", ""))
        subpoints_raw = entry.get("subpoints") or entry.get("detail")
        if isinstance(subpoints_raw, list):
            subpoints = [_normalize_text(item) for item in subpoints_raw if _normalize_text(item)]
        elif isinstance(subpoints_raw, str):
            subpoints = [_normalize_text(subpoints_raw)]
        else:
            subpoints = []
        if not summary or not subpoints:
            continue
        evidence_refs = entry.get("evidence_refs") or entry.get("evidence") or []
        citations: List[EvidenceSpan] = []
        for ref in evidence_refs:
            chunk = evidence_map.get(ref)
            if not chunk:
                continue
            citations.append(
                EvidenceSpan(
                    source_id=chunk.get("source_id", "unknown"),
                    page=chunk.get("page", 1),
                    char_start=chunk.get("char_start", 0),
                    char_end=chunk.get("char_end", 0),
                    quote=_clip_quote(chunk.get("text", "")),
                    chunk_id=chunk.get("id"),
                    chunk_text=chunk.get("text"),
                )
            )
        if not citations:
            continue
        confidence = entry.get("confidence")
        try:
            confidence_val = float(confidence) if confidence is not None else 0.7
        except (TypeError, ValueError):
            confidence_val = 0.7
        detail_text = " ".join(
            point if point.endswith(".") else f"{point}." for point in subpoints
        )
        claims.append(
            Claim(
                id=f"c{len(claims) + 1:04d}",
                topic=topic,
                summary=summary if summary.endswith(".") else f"{summary}.",
                text=detail_text,
                subpoints=[
                    point if point.endswith(".") else f"{point}." for point in subpoints
                ],
                citations=citations,
                confidence=max(0.0, min(1.0, confidence_val)),
                status="draft",
            )
        )
        if len(claims) >= MAX_CLAIMS:
            break

    return claims


def _fallback_claims(topic: str, hits: Sequence[dict]) -> List[Claim]:
    sentences = list(_yield_sentences(hits))
    claims: List[Claim] = []
    if not sentences:
        return claims
    group_size = max(3, len(sentences) // MAX_CLAIMS or 1)
    idx = 0
    while idx < len(sentences) and len(claims) < MAX_CLAIMS:
        group = sentences[idx : idx + group_size]
        idx += group_size
        summaries = [sentence for sentence, _, _ in group]
        subpoints = [
            sentence if sentence.endswith(".") else f"{sentence}." for sentence in summaries
        ]
        detail = " ".join(subpoints)
        summary_text = summaries[0]
        citations = [
            _make_evidence_span(hit, sentence, rel_idx)
            for sentence, hit, rel_idx in group
        ]
        claims.append(
            Claim(
                id=f"c{len(claims) + 1:04d}",
                topic=topic,
                summary=summary_text if summary_text.endswith(".") else f"{summary_text}.",
                text=detail,
                subpoints=subpoints,
                citations=citations,
                confidence=0.55,
                status="draft",
            )
        )
    while len(claims) < MIN_CLAIMS and sentences:
        sentence, hit, rel_idx = sentences[len(claims) % len(sentences)]
        span = _make_evidence_span(hit, sentence, rel_idx)
        subpoint = sentence if sentence.endswith(".") else f"{sentence}."
        claims.append(
            Claim(
                id=f"c{len(claims) + 1:04d}",
                topic=topic,
                summary=sentence,
                text=subpoint,
                subpoints=[subpoint],
                citations=[span],
                confidence=0.5,
                status="draft",
            )
        )
    return claims


def _aggregate_verdict(evals: List[Tuple[str, str]]) -> str:
    verdicts = [verdict for verdict, _ in evals]
    if any(verdict == "Contradicted" for verdict in verdicts):
        return "Contradicted"
    if any(verdict == "Weak" for verdict in verdicts):
        return "Weak"
    return "Supported"


def _llm_synthesizer(
    topic: str,
    reviewed: List[ReviewedClaim],
    challenges: Optional[List[RedTeamFinding]],
) -> List[Insight]:
    usable_claims = [c for c in reviewed if c.verdict in {"Supported", "Weak"}]
    if not usable_claims:
        logger.warning("No Supported/Weak claims to synthesize.")
        return []
    claim_lines = [
        f"{claim.id} ({claim.verdict}): {claim.text}" for claim in usable_claims
    ]
    challenge_lines = [
        f"{challenge.claim_id}: {challenge.summary}" for challenge in (challenges or [])
    ]
    system_prompt = (
        "You are Synthesizer. Cluster related reviewed claims and challenges into 3-5 thematic insights. "
        "For each cluster, write a concise summary sentence and a detailed 3-6 sentence explanation that "
        "references the supporting claim IDs, acknowledges overlapping challenges, and explains the overall implication. "
        "Do not repeat raw text; synthesize. Output JSON list with objects "
        "{\"summary\": \"...\", \"detail\": \"...\", \"claim_ids\": [\"c0001\", ...], "
        "\"confidence\": 0-1}. Only reference provided claim IDs."
    )
    user_prompt = (
        f"Topic: {topic}\nReviewed claims:\n"
        + "\n".join(claim_lines)
        + ("\nChallenges:\n" + "\n".join(challenge_lines) if challenge_lines else "")
    )
    try:
        llm_output = call_llm_json(system_prompt, user_prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Synthesizer LLM failed: %s", exc)
        return []

    claim_lookup = {claim.id: claim for claim in reviewed}
    insights: List[Insight] = []
    for entry in llm_output:
        summary = _normalize_text(entry.get("summary", ""))
        detail = _normalize_text(entry.get("detail", entry.get("text", "")))
        if not summary or not detail:
            continue
        claim_ids = [cid for cid in entry.get("claim_ids", []) if cid in claim_lookup]
        if not claim_ids:
            continue
        provenance: List[EvidenceSpan] = []
        for cid in claim_ids:
            provenance.extend(claim_lookup[cid].citations)
        try:
            confidence = float(entry.get("confidence", 0.75))
        except (TypeError, ValueError):
            confidence = 0.75
        detail_text = detail if detail.endswith(".") else f"{detail}."
        summary_text = summary if summary.endswith(".") else f"{summary}."
        insights.append(
            Insight(
                id=f"i{len(insights) + 1:04d}",
                topic=topic,
                claim_ids=claim_ids,
                summary=summary_text,
                text=detail_text,
                confidence=max(0.0, min(1.0, confidence)),
                provenance=provenance,
            )
        )
        if len(insights) >= 5:
            break
    return insights


def _fallback_insights(topic: str, reviewed: List[ReviewedClaim]) -> List[Insight]:
    supported = [claim for claim in reviewed if claim.verdict == "Supported"]
    weak = [claim for claim in reviewed if claim.verdict == "Weak"]
    if not supported and not weak:
        logger.warning("No reviewed claims available to synthesize insights.")
        return []
    selected_claims = supported or weak[:3]
    insights: List[Insight] = []
    chunk_size = max(1, len(selected_claims) // 3 + (1 if len(selected_claims) > 3 else 0))
    for idx in range(0, len(selected_claims), chunk_size):
        group = selected_claims[idx : idx + chunk_size]
        text = " ".join(claim.text for claim in group)
        claim_ids = [claim.id for claim in group]
        provenance = [span for claim in group for span in claim.citations]
        summary = group[0].text.split(".")[0]
        insight = Insight(
            id=f"i{len(insights) + 1:04d}",
            topic=topic,
            claim_ids=claim_ids,
            summary=summary if summary.endswith(".") else f"{summary}.",
            text=text,
            confidence=min(0.95, sum((claim.confidence or 0.6) for claim in group) / len(group)),
            provenance=provenance,
        )
        insights.append(insight)
        if len(insights) >= 5:
            break
    return insights


def _gather_counter_evidence(claim: ReviewedClaim, total: int = 6) -> List[dict]:
    queries = [
        claim.text,
        f"limitations of: {claim.text[:180]}",
        f"counter argument to: {claim.text[:180]}",
    ]
    seen = set()
    hits: List[dict] = []
    for query in queries:
        results = search(query, k=total // len(queries) + 2)
        for res in results:
            chunk_id = res.get("id")
            if chunk_id in seen:
                continue
            seen.add(chunk_id)
            # skip evidence already cited
            if any(span.chunk_id == chunk_id for span in claim.citations):
                continue
            hits.append(res)
            if len(hits) >= total:
                return hits
    return hits
