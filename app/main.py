"""Streamlit UI for Collective Insight Lab."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
import logging
from typing import List

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents import (  # type: ignore  # noqa: E402
    load_claims_from_artifacts,
    load_insights_from_artifacts,
    reset_artifacts,
    run_action_planner,
    run_red_team,
    run_researcher,
    run_reviewer,
    run_synthesizer,
)
from app.graph import build_reasoning_graph  # type: ignore  # noqa: E402
from app.ingestion import ingest_dir  # type: ignore  # noqa: E402
from app.schemas import (
    ActionItem,
    Claim,
    EvidenceSpan,
    Insight,
    RedTeamFinding,
    ReviewedClaim,
)  # type: ignore  # noqa: E402
from app.utils import configure_logging, ensure_dirs  # type: ignore  # noqa: E402
from app.vectorstore import get_collection, reset_vector_store  # type: ignore  # noqa: E402

configure_logging()
logger = logging.getLogger(__name__)

DOCS_DIR = Path("pdf_workspace")
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ".data/chroma")).expanduser()
ensure_dirs(DOCS_DIR, "artifacts")
ARTIFACTS_DIR = Path("artifacts")
DEMO_STAGE_DELAY = 7

SUMMARY_STAGES = ["researcher", "red_team", "synthesizer"]
STAGE_LABELS = {
    "researcher": "Researcher & Reviewer",
    "red_team": "Red Team",
    "synthesizer": "Synthesizer & Actions",
}

LEVEL_STYLES = {
    "info": {"bg": "#eef5ff", "fg": "#0b3d91", "border": "#d6e4ff"},
    "info-running": {"bg": "#fff4e5", "fg": "#a15c00", "border": "#fdd8b1"},
    "success": {"bg": "#e6f4ea", "fg": "#0f5132", "border": "#bfe3c5"},
    "error": {"bg": "#fdecea", "fg": "#842029", "border": "#f5c1bc"},
}

BADGE_STYLES = {
    "done": {"bg": "#e6f4ea", "fg": "#0f5132", "border": "#bfe3c5"},
    "running": {"bg": "#fff4e5", "fg": "#a15c00", "border": "#fdd8b1"},
    "pending": {"bg": "#f2f4f7", "fg": "#5f6368", "border": "#d0d4db"},
}



def _clear_dir_contents(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def initialize_workspace(clear_chroma: bool = True) -> None:
    if st.session_state.get("_workspace_initialized"):
        return
    if clear_chroma and CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    _clear_dir_contents(DOCS_DIR)
    ensure_dirs(DOCS_DIR, "artifacts")
    reset_artifacts(include_claims=True)
    st.session_state["_workspace_initialized"] = True


def _vector_store_ready() -> bool:
    """Return True if Chroma collection exists and has data."""
    try:
        collection = get_collection()
        has_docs = collection.count() > 0
        if not has_docs:
            logger.info("Vector store is empty; ingestion required before running agents.")
        return has_docs
    except Exception as exc:  # noqa: BLE001
        logger.warning("Vector store unavailable (%s); resetting.", exc)
        try:
            reset_vector_store()
        except Exception as reset_exc:  # noqa: BLE001
            logger.error("Failed to reset vector store: %s", reset_exc)
        return False


def _ensure_stage_tracker(reset: bool = False) -> dict[str, str]:
    if reset or "stage_tracker" not in st.session_state:
        st.session_state["stage_tracker"] = {stage: "pending" for stage in SUMMARY_STAGES}
    return st.session_state["stage_tracker"]


def _set_stage_status(stage: str, status: str) -> None:
    tracker = _ensure_stage_tracker()
    if stage in tracker:
        tracker[stage] = status


def _stage_summary_tooltip() -> str:
    tracker = _ensure_stage_tracker()
    icon_map = {"pending": "○", "running": "⟳", "done": "✓"}
    lines = ["Stage progress:"]
    for stage in SUMMARY_STAGES:
        status = tracker.get(stage, "pending")
        label = STAGE_LABELS.get(stage, stage.title())
        lines.append(f"{icon_map.get(status, '○')} {label}")
    return "\n".join(lines)


def _stage_summary_caption() -> str:
    tracker = _ensure_stage_tracker()
    icon_map = {"pending": "○", "running": "⟳", "done": "✓"}
    badges = []
    for stage in SUMMARY_STAGES:
        status = tracker.get(stage, "pending")
        label = STAGE_LABELS.get(stage, stage.title())
        icon = icon_map.get(status, "○")
        style = BADGE_STYLES.get(status, BADGE_STYLES["pending"])
        badge_html = (
            "<span style=\"display:inline-flex;align-items:center;padding:0.15rem 0.55rem;"
            "border-radius:999px;font-weight:600;margin:0.15rem 0.35rem 0 0;"
            f"background:{style['bg']};color:{style['fg']};border:1px solid {style['border']};\">"
            f"{icon}&nbsp;{label}</span>"
        )
        badges.append(badge_html)
    return "<div style='margin-top:0.35rem;display:flex;flex-wrap:wrap;'>%s</div>" % "".join(badges)


def _status_style(level: str) -> dict[str, str]:
    return LEVEL_STYLES.get(level, LEVEL_STYLES["info"])


def _write_artifact(filename: str, data: object) -> None:
    target = ARTIFACTS_DIR / filename
    target.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _demo_sleep() -> None:
    time.sleep(DEMO_STAGE_DELAY)


def _demo_claims(topic: str) -> List[Claim]:
    seeds = [
        (
            "Agent debate improves recall.",
            "Parallel researcher-reviewer loops surface 30% more unique citations across climate-tech PDFs.",
            "Parallel reviewer loops uncovered additional supporting paragraphs.",
        ),
        (
            "Red-team prompts cut hallucinations.",
            "Injecting contradiction hunts after every third claim halves unsupported statements.",
            "Contradiction hunts reduce unsupported statements.",
        ),
        (
            "Synthesizers need provenance summaries.",
            "Claims grounded with short, line-level provenance earned higher judge trust in user tests.",
            "Line-level provenance improves trust.",
        ),
    ]
    claims: List[Claim] = []
    for idx, (summary, detail, quote) in enumerate(seeds, start=1):
        citation = EvidenceSpan(
            source_id=f"demo_source_{idx}",
            page=idx,
            char_start=0,
            char_end=len(quote),
            quote=quote,
        )
        claims.append(
            Claim(
                id=f"c{idx:04d}",
                topic=topic,
                summary=summary,
                text=detail,
                subpoints=[detail],
                citations=[citation],
                confidence=min(0.95, 0.78 + idx * 0.05),
                status="draft",
            )
        )
    return claims


def _run_demo_researcher(topic: str) -> List[Claim]:
    reset_artifacts(include_claims=False)
    claims = _demo_claims(topic)
    _write_artifact("claims.json", [claim.model_dump() for claim in claims])
    return claims


def _run_demo_red_team(topic: str, reviewed: List[ReviewedClaim]) -> List[RedTeamFinding]:
    if not reviewed:
        return []
    targets = reviewed[:2]
    findings: List[RedTeamFinding] = []
    templates = [
        (
            "Need stronger baselines.",
            "The claim cites higher recall but does not compare against a single-agent baseline within the same corpus.",
            "Medium",
        ),
        (
            "Provenance summaries still manual.",
            "Evidence points to higher trust but interviews reveal analysts still curate provenance by hand.",
            "Low",
        ),
    ]
    for idx, (claim, template) in enumerate(zip(targets, templates, strict=False), start=1):
        summary, detail, severity = template
        evidence = claim.citations[:1] if claim.citations else []
        findings.append(
            RedTeamFinding(
                id=f"r{idx:04d}",
                topic=topic,
                claim_id=claim.id,
                claim_text=claim.text,
                summary=summary,
                detail=detail if detail.endswith(".") else f"{detail}.",
                evidence=evidence,
                severity=severity,  # type: ignore[arg-type]
                actions=[
                    "Collect apples-to-apples baseline metrics.",
                    "Document manual provenance workflow pain points.",
                ],
            )
        )
    _write_artifact("challenges.json", [finding.model_dump() for finding in findings])
    return findings


def _run_demo_synthesizer(
    topic: str,
    reviewed: List[ReviewedClaim],
    challenges: List[RedTeamFinding],
) -> List[Insight]:
    if not reviewed:
        return []
    claim_map = {claim.id: claim for claim in reviewed}
    insight_specs = [
        (
            "Agent debate widens coverage.",
            ["c0001", "c0002"],
            "Researcher/Reviewer exchanges surface more unique passages while red-team checks keep hallucinations low.",
            0.88,
        ),
        (
            "Explainability drives adoption.",
            ["c0003"],
            "Line-level provenance summaries make it easier for analysts to reuse synthesized insights in reports.",
            0.82,
        ),
    ]
    insights: List[Insight] = []
    for idx, (summary, claim_ids, text, confidence) in enumerate(insight_specs, start=1):
        provenance = []
        for cid in claim_ids:
            claim = claim_map.get(cid)
            if claim:
                provenance.extend(claim.citations)
        insights.append(
            Insight(
                id=f"i{idx:04d}",
                topic=topic,
                claim_ids=claim_ids,
                summary=summary,
                text=text if text.endswith(".") else f"{text}.",
                confidence=confidence,
                provenance=provenance,
            )
        )
    report_payload = {
        "insights": [insight.model_dump() for insight in insights],
        "actions": [],
        "challenges": [challenge.model_dump() for challenge in challenges],
    }
    _write_artifact("report.json", report_payload)
    return insights


def _run_demo_action_planner(
    topic: str,
    reviewed: List[ReviewedClaim],
    insights: List[Insight],
) -> List[ActionItem]:
    related_claims = reviewed[:2]
    actions = [
        ActionItem(
            id="a0001",
            topic=topic,
            title="Benchmark against single-agent runs",
            detail="Replay 3 representative topics with a solo LLM to quantify recall uplift.",
            tag="NextStep",
            related_claims=[claim.id for claim in related_claims],
        ),
        ActionItem(
            id="a0002",
            topic=topic,
            title="Prototype auto-provenance writer",
            detail="Use reviewer notes to auto-generate provenance blurbs instead of manual curation.",
            tag="Hypothesis",
            related_claims=[related_claims[0].id] if related_claims else [],
        ),
    ]
    _write_artifact("actions.json", [action.model_dump() for action in actions])
    report_path = ARTIFACTS_DIR / "report.json"
    if report_path.exists():
        data = json.loads(report_path.read_text(encoding="utf-8"))
    else:
        data = {"insights": [insight.model_dump() for insight in insights], "challenges": [], "actions": []}
    data["actions"] = [action.model_dump() for action in actions]
    report_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return actions


def _execute_researcher(topic: str, demo_mode: bool) -> List[Claim]:
    if demo_mode:
        _demo_sleep()
        return _run_demo_researcher(topic)
    return run_researcher(topic)


def _execute_red_team(topic: str, reviewed: List[ReviewedClaim], demo_mode: bool) -> List[RedTeamFinding]:
    if demo_mode:
        _demo_sleep()
        return _run_demo_red_team(topic, reviewed)
    return run_red_team(topic, reviewed)


def _execute_synthesizer(
    topic: str,
    reviewed: List[ReviewedClaim],
    challenges: List[RedTeamFinding],
    demo_mode: bool,
) -> List[Insight]:
    if demo_mode:
        _demo_sleep()
        return _run_demo_synthesizer(topic, reviewed, challenges)
    return run_synthesizer(topic, reviewed, challenges)


def _execute_action_planner(
    topic: str,
    reviewed: List[ReviewedClaim],
    insights: List[Insight],
    demo_mode: bool,
) -> List[ActionItem]:
    if demo_mode:
        _demo_sleep()
        return _run_demo_action_planner(topic, reviewed, insights)
    return run_action_planner(topic, reviewed, insights)


def _load_reviewed_claims() -> List[ReviewedClaim]:
    path = Path("artifacts/claims_reviewed.json")
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ReviewedClaim.model_validate(entry) for entry in data]


def _load_insights() -> List[Insight]:
    path = Path("artifacts/report.json")
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        raw_insights = data
    else:
        raw_insights = data.get("insights", [])
    return [Insight.model_validate(entry) for entry in raw_insights]


def _load_actions() -> List[ActionItem]:
    path = Path("artifacts/actions.json")
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [ActionItem.model_validate(entry) for entry in data]


def _load_challenges() -> List[RedTeamFinding]:
    path = Path("artifacts/challenges.json")
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [RedTeamFinding.model_validate(entry) for entry in data]


def _build_placeholders() -> dict[str, DeltaGenerator]:
    placeholders: dict[str, DeltaGenerator] = {}
    placeholders["status"] = st.empty()

    with st.container():
        st.subheader("Reasoning Graph")
        placeholders["graph"] = st.empty()

    with st.container():
        st.subheader("Reviewed Claims")
        placeholders["claims"] = st.empty()

    with st.container():
        st.subheader("Red Team Challenges")
        placeholders["challenges"] = st.empty()

    with st.container():
        st.subheader("Insights")
        placeholders["insights"] = st.empty()

    with st.container():
        st.subheader("Suggested Actions & Next Hypotheses")
        placeholders["actions"] = st.empty()

    return placeholders


def _current_stage() -> str:
    return st.session_state.get("current_stage", "ingestion")


def _set_stage(stage: str) -> None:
    st.session_state["current_stage"] = stage


def _render_graph(container: DeltaGenerator) -> None:
    container.empty()
    container.graphviz_chart(build_reasoning_graph(stage=_current_stage()))


def _render_claims(container: DeltaGenerator) -> None:
    container.empty()
    body = container.container()
    reviewed_claims = _load_reviewed_claims()
    if not reviewed_claims:
        body.info("No reviewed claims yet. Run the pipeline to populate this section.")
    else:
        for claim in reviewed_claims:
            summary = claim.summary or claim.text.split(".")[0]
            label = f"{claim.id} · {summary}"
            with body.expander(label):
                st.write(claim.text)
                st.caption(", ".join(f"{span.source_id} p{span.page}" for span in claim.citations))


def _render_challenges(container: DeltaGenerator) -> None:
    container.empty()
    body = container.container()
    challenges = _load_challenges()
    if not challenges:
        body.info("Run the Red Team to discover contradictions or gaps.")
    else:
        for finding in challenges:
            label = f"{finding.summary} · {finding.severity} (Claim {finding.claim_id})"
            with body.expander(label):
                st.write(finding.detail)
                st.caption(", ".join(f"{span.source_id} p{span.page}" for span in finding.evidence))
                if finding.actions:
                    st.markdown("**Suggested follow-ups:**")
                    for action in finding.actions:
                        st.markdown(f"- {action}")


def _render_insights(container: DeltaGenerator) -> None:
    container.empty()
    body = container.container()
    insights = _load_insights()
    if not insights:
        body.info("No insights available. Generate them after running Red Team.")
    else:
        for insight in insights:
            with body.expander(f"{insight.id} · {insight.summary} · Confidence {insight.confidence:.2f}"):
                st.write(insight.text)
                st.caption(", ".join(f"{span.source_id} p{span.page}" for span in insight.provenance))


def _render_actions(container: DeltaGenerator) -> None:
    container.empty()
    body = container.container()
    actions = _load_actions()
    if not actions:
        body.info("Generate insights to see suggested actions.")
    else:
        for action in actions:
            label = f"{action.title} · {action.tag}"
            with body.expander(label):
                st.write(action.detail)
                if action.related_claims:
                    st.caption(f"Related claims: {', '.join(action.related_claims)}")


def _update_sections(placeholders: dict[str, DeltaGenerator]) -> None:
    _render_graph(placeholders["graph"])
    _render_claims(placeholders["claims"])
    _render_challenges(placeholders["challenges"])
    _render_insights(placeholders["insights"])
    _render_actions(placeholders["actions"])


def _escape_tooltip(text: str) -> str:
    return text.replace("\"", "&quot;").replace("\n", "&#10;")


def _set_status_message(
    placeholder: DeltaGenerator,
    message: str,
    level: str = "info",
    tooltip: str | None = None,
    details: str | None = None,
    details_is_html: bool = False,
) -> None:
    placeholder.empty()
    container = placeholder.container()
    style = _status_style(level)
    box_style = (
        "padding:0.8rem 1rem;border-radius:10px;margin-bottom:0.25rem;"
        f"background:{style['bg']};color:{style['fg']};"
        f"border:1px solid {style['border']};font-weight:600;"
        "display:flex;justify-content:space-between;align-items:center;gap:0.75rem;"
    )
    icon_html = ""
    if tooltip:
        icon_html = (
            f"<span style='width:1.35rem;height:1.35rem;border-radius:50%;"
            "display:inline-flex;align-items:center;justify-content:center;"
            "font-weight:700;font-size:0.85rem;background:#f2f4f7;color:#5f6368;"
            f"border:1px solid rgba(0,0,0,0.08);' title='{_escape_tooltip(tooltip)}'>i</span>"
        )
    container.markdown(
        f"<div style=\"{box_style}\"><span>{message}</span>{icon_html}</div>",
        unsafe_allow_html=True,
    )
    if details:
        if details_is_html:
            container.markdown(details, unsafe_allow_html=True)
        else:
            container.caption(details)


def main() -> None:
    st.set_page_config(page_title="Collective Insight Lab", layout="wide")
    st.session_state.setdefault("clear_chroma_on_start", False)
    st.session_state.setdefault("current_stage", "ingestion")
    _ensure_stage_tracker()
    initialize_workspace(clear_chroma=st.session_state["clear_chroma_on_start"])
    st.title("Collective Insight Lab")
    placeholders = _build_placeholders()
    status_placeholder = placeholders["status"]
    _update_sections(placeholders)

    with st.sidebar:
        st.subheader("Workspace")
        clear_toggle = st.toggle(
            "Clear Chroma on start",
            value=st.session_state["clear_chroma_on_start"],
            help="Reset the vector store whenever the app initializes.",
        )
        if clear_toggle != st.session_state["clear_chroma_on_start"]:
            st.session_state["clear_chroma_on_start"] = clear_toggle
            st.session_state["_workspace_initialized"] = False
            st.experimental_rerun()

        demo_mode = st.toggle(
            "Demo mode (mock agents)",
            value=st.session_state.get("demo_mode", False),
            help="Use canned agent outputs to exercise the UI without LLM calls.",
        )
        st.session_state["demo_mode"] = demo_mode
        if demo_mode:
            st.info("Demo mode enabled: stages return mocked data with short waits.")

        st.header("Corpus")
        uploaded_files = st.file_uploader(
            "Upload PDFs",
            type=["pdf"],
            accept_multiple_files=True,
        )
        if st.button("Reset Artifacts"):
            reset_artifacts(include_claims=True)
            _ensure_stage_tracker(reset=True)
            st.success("Cleared artifacts folder.")
        if st.button("Ingest Uploaded PDFs") and uploaded_files:
            tmp_dir = Path(tempfile.mkdtemp())
            for file in uploaded_files:
                target = tmp_dir / file.name
                target.write_bytes(file.getvalue())
            _set_status_message(
                status_placeholder,
                "Ingesting uploaded PDFs...",
                "info",
                tooltip=_stage_summary_tooltip(),
                details=_stage_summary_caption(),
                details_is_html=True,
            )
            ingest_dir(tmp_dir)
            st.success("Uploaded PDFs ingested successfully.")
            _set_stage("ingestion")
            _ensure_stage_tracker(reset=True)
            _set_status_message(
                status_placeholder,
                "Ingestion completed.",
                "success",
                tooltip=_stage_summary_tooltip(),
                details=_stage_summary_caption(),
                details_is_html=True,
            )
            _update_sections(placeholders)

        topic = st.text_input("Topic / Prompt", "")
        run_pipeline_btn = st.button("Run Researcher + Reviewer")
        run_red_team_btn = st.button("Run Red Team")
        generate_insights_btn = st.button("Generate Insights & Next Steps")
        run_full_pipeline_btn = st.button("Run Full Pipeline")

    demo_mode = st.session_state.get("demo_mode", False)
    raw_topic = topic.strip()
    default_demo_topic = "Demo Topic (mock)"

    if run_pipeline_btn:
        if not raw_topic and not demo_mode:
            st.error("Please enter a topic before running the pipeline.")
        elif not _vector_store_ready() and not demo_mode:
            st.error("No documents found in the vector store. Upload and ingest PDFs first.")
        else:
            _set_stage_status("researcher", "running")
            _set_status_message(
                status_placeholder,
                "Running Researcher + Reviewer...",
                "info-running",
                tooltip=_stage_summary_tooltip(),
                details=_stage_summary_caption(),
                details_is_html=True,
            )
            claims = _execute_researcher(raw_topic or default_demo_topic, demo_mode)
            reviewed = run_reviewer(claims)
            st.success("Researcher + Reviewer finished. Reviewed claims table updated.")
            _set_stage("researcher")
            _set_stage_status("researcher", "done")
            _set_status_message(
                status_placeholder,
                "Researcher + Reviewer finished.",
                "success",
                tooltip=_stage_summary_tooltip(),
                details=_stage_summary_caption(),
                details_is_html=True,
            )
            _update_sections(placeholders)

    if run_red_team_btn:
        reviewed = _load_reviewed_claims()
        if not reviewed:
            st.error("No reviewed claims found. Run the pipeline first.")
        elif not _vector_store_ready() and not demo_mode:
            st.error("No documents found in the vector store. Upload and ingest PDFs first.")
        else:
            current_topic = raw_topic or reviewed[0].topic or default_demo_topic
            _set_stage_status("researcher", "done")
            _set_stage_status("red_team", "running")
            _set_status_message(
                status_placeholder,
                "Running Red Team...",
                "info-running",
                tooltip=_stage_summary_tooltip(),
                details=_stage_summary_caption(),
                details_is_html=True,
            )
            findings = _execute_red_team(current_topic, reviewed, demo_mode)
            if findings:
                st.success("Red Team findings updated.")
            else:
                st.warning("Red Team did not find clear contradictions.")
            _set_stage("red_team")
            _set_stage_status("red_team", "done")
            _set_status_message(
                status_placeholder,
                "Red Team stage completed.",
                "success",
                tooltip=_stage_summary_tooltip(),
                details=_stage_summary_caption(),
                details_is_html=True,
            )
            _update_sections(placeholders)

    if generate_insights_btn:
        reviewed = _load_reviewed_claims()
        if not reviewed:
            st.error("No reviewed claims found. Run the pipeline first.")
        elif not _vector_store_ready() and not demo_mode:
            st.error("No documents found in the vector store. Upload and ingest PDFs first.")
        else:
            current_topic = raw_topic or reviewed[0].topic or default_demo_topic
            challenges = _load_challenges()
            _set_stage_status("red_team", "done")
            _set_stage_status("synthesizer", "running")
            _set_status_message(
                status_placeholder,
                "Synthesizing insights and actions...",
                "info-running",
                tooltip=_stage_summary_tooltip(),
                details=_stage_summary_caption(),
                details_is_html=True,
            )
            insights = _execute_synthesizer(current_topic, reviewed, challenges, demo_mode)
            actions = _execute_action_planner(current_topic, reviewed, insights, demo_mode)
            if insights:
                st.success("Insights generated and report updated.")
            if actions:
                st.info("Suggested actions refreshed.")
            _set_stage("synthesizer")
            _set_stage_status("synthesizer", "done")
            _set_status_message(
                status_placeholder,
                "Insights and actions updated.",
                "success",
                tooltip=_stage_summary_tooltip(),
                details=_stage_summary_caption(),
                details_is_html=True,
            )
            _update_sections(placeholders)

    if run_full_pipeline_btn:
        effective_topic = raw_topic or (default_demo_topic if demo_mode else "")
        if not effective_topic:
            st.error("Please enter a topic before running the full pipeline.")
        elif not _vector_store_ready() and not demo_mode:
            st.error("No documents found in the vector store. Upload and ingest PDFs first.")
        else:
            try:
                _ensure_stage_tracker(reset=True)
                _set_stage_status("researcher", "running")
                _set_status_message(
                    status_placeholder,
                    "Running Researcher agent...",
                    "info-running",
                    tooltip=_stage_summary_tooltip(),
                    details=_stage_summary_caption(),
                    details_is_html=True,
                )
                claims = _execute_researcher(effective_topic, demo_mode)

                _set_status_message(
                    status_placeholder,
                    "Auto-reviewing claims...",
                    "info-running",
                    tooltip=_stage_summary_tooltip(),
                    details=_stage_summary_caption(),
                    details_is_html=True,
                )
                reviewed = run_reviewer(claims)
                time.sleep(0.2)
                _set_stage("researcher")
                _set_stage_status("researcher", "done")
                _set_status_message(
                    status_placeholder,
                    "Researcher stage complete.",
                    "success",
                    tooltip=_stage_summary_tooltip(),
                    details=_stage_summary_caption(),
                    details_is_html=True,
                )
                _update_sections(placeholders)

                _set_stage_status("red_team", "running")
                _set_status_message(
                    status_placeholder,
                    "Running Red Team agent...",
                    "info-running",
                    tooltip=_stage_summary_tooltip(),
                    details=_stage_summary_caption(),
                    details_is_html=True,
                )
                findings = _execute_red_team(effective_topic, reviewed, demo_mode)
                _set_stage("red_team")
                _set_stage_status("red_team", "done")
                _set_status_message(
                    status_placeholder,
                    "Red Team stage complete.",
                    "success",
                    tooltip=_stage_summary_tooltip(),
                    details=_stage_summary_caption(),
                    details_is_html=True,
                )
                _update_sections(placeholders)

                _set_stage_status("synthesizer", "running")
                _set_status_message(
                    status_placeholder,
                    "Synthesizing insights and actions...",
                    "info-running",
                    tooltip=_stage_summary_tooltip(),
                    details=_stage_summary_caption(),
                    details_is_html=True,
                )
                insights = _execute_synthesizer(effective_topic, reviewed, findings, demo_mode)
                actions = _execute_action_planner(effective_topic, reviewed, insights, demo_mode)
                _set_stage("synthesizer")
                _set_stage_status("synthesizer", "done")
                _set_status_message(
                    status_placeholder,
                    "Synthesis stage complete.",
                    "success",
                    tooltip=_stage_summary_tooltip(),
                    details=_stage_summary_caption(),
                    details_is_html=True,
                )
                _update_sections(placeholders)

                _set_stage("complete")
                tooltip = _stage_summary_tooltip()
                caption = _stage_summary_caption()
                _set_status_message(
                    status_placeholder,
                    "Full pipeline completed successfully.",
                    "success",
                    tooltip=tooltip,
                    details=caption,
                    details_is_html=True,
                )
                _update_sections(placeholders)
            except Exception as exc:  # noqa: BLE001
                tooltip = _stage_summary_tooltip()
                _set_status_message(
                    status_placeholder,
                    f"Full pipeline failed: {exc}",
                    "error",
                    tooltip=tooltip,
                    details=_stage_summary_caption(),
                    details_is_html=True,
                )


if __name__ == "__main__":
    main()
