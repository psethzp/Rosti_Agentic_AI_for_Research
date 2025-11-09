"""Streamlit UI for Collective Insight Lab."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import List

import streamlit as st

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
from app.schemas import ActionItem, Insight, RedTeamFinding, ReviewedClaim  # type: ignore  # noqa: E402
from app.utils import configure_logging, ensure_dirs  # type: ignore  # noqa: E402

configure_logging()

DOCS_DIR = Path("pdf_workspace")
CHROMA_DIR = Path(os.getenv("CHROMA_DIR", ".data/chroma")).expanduser()
ensure_dirs(DOCS_DIR, "artifacts")


def _clear_dir_contents(path: Path) -> None:
    if not path.exists():
        return
    for child in path.iterdir():
        if child.is_dir():
            shutil.rmtree(child)
        else:
            child.unlink()


def initialize_workspace() -> None:
    if st.session_state.get("_workspace_initialized"):
        return
    if CHROMA_DIR.exists():
        shutil.rmtree(CHROMA_DIR)
    _clear_dir_contents(DOCS_DIR)
    ensure_dirs(DOCS_DIR, "artifacts")
    reset_artifacts(include_claims=True)
    st.session_state["_workspace_initialized"] = True


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


def main() -> None:
    st.set_page_config(page_title="Collective Insight Lab", layout="wide")
    initialize_workspace()
    st.title("Collective Insight Lab")

    with st.sidebar:
        st.header("Corpus")
        uploaded_files = st.file_uploader(
            "Upload PDFs",
            type=["pdf"],
            accept_multiple_files=True,
        )
        if st.button("Reset Artifacts"):
            reset_artifacts(include_claims=True)
            st.success("Cleared artifacts folder.")
        if st.button("Ingest Uploaded PDFs") and uploaded_files:
            tmp_dir = Path(tempfile.mkdtemp())
            for file in uploaded_files:
                target = tmp_dir / file.name
                target.write_bytes(file.getvalue())
            ingest_dir(tmp_dir)
            st.success("Uploaded PDFs ingested successfully.")

        topic = st.text_input("Topic / Prompt", "")
        run_pipeline_btn = st.button("Run Researcher + Reviewer")
        run_red_team_btn = st.button("Run Red Team")
        generate_insights_btn = st.button("Generate Insights & Next Steps")

    if run_pipeline_btn:
        if not topic.strip():
            st.error("Please enter a topic before running the pipeline.")
        else:
            with st.spinner("Running Researcher and Reviewer..."):
                run_researcher(topic)
                time.sleep(1)
                claims = load_claims_from_artifacts()
                reviewed = run_reviewer(claims)
            st.success("Researcher + Reviewer finished. Reviewed claims table updated.")

    if run_red_team_btn:
        reviewed = _load_reviewed_claims()
        if not reviewed:
            st.error("No reviewed claims found. Run the pipeline first.")
        else:
            current_topic = topic or reviewed[0].topic
            with st.spinner("Running Red Team to find contradictions..."):
                findings = run_red_team(current_topic, reviewed)
            if findings:
                st.success("Red Team findings updated.")
            else:
                st.warning("Red Team did not find clear contradictions.")

    if generate_insights_btn:
        reviewed = _load_reviewed_claims()
        if not reviewed:
            st.error("No reviewed claims found. Run the pipeline first.")
        else:
            current_topic = topic or reviewed[0].topic
            challenges = _load_challenges()
            with st.spinner("Generating insights and suggested actions..."):
                insights = run_synthesizer(current_topic, reviewed, challenges)
                actions = run_action_planner(current_topic, reviewed, insights)
            if insights:
                st.success("Insights generated and report updated.")
            if actions:
                st.info("Suggested actions refreshed.")

    st.subheader("Reasoning Graph")
    st.graphviz_chart(build_reasoning_graph(include_red_team=True))

    st.subheader("Reviewed Claims")
    reviewed_claims = _load_reviewed_claims()
    if not reviewed_claims:
        st.info("No reviewed claims yet. Run the pipeline to populate this section.")
    else:
        for claim in reviewed_claims:
            summary = claim.summary or claim.text.split(".")[0]
            label = f"{claim.id} · {summary}"
            with st.expander(label):
                st.write(claim.text)
                st.caption(
                    ", ".join(
                        f"{span.source_id} p{span.page}" for span in claim.citations
                    )
                )

    st.subheader("Red Team Challenges")
    challenges = _load_challenges()
    if not challenges:
        st.info("Run the Red Team to discover contradictions or gaps.")
    else:
        for finding in challenges:
            label = f"{finding.summary} · {finding.severity} (Claim {finding.claim_id})"
            with st.expander(label):
                st.write(finding.detail)
                st.caption(
                    ", ".join(
                        f"{span.source_id} p{span.page}" for span in finding.evidence
                    )
                )
                if finding.actions:
                    st.markdown("**Suggested follow-ups:**")
                    for action in finding.actions:
                        st.markdown(f"- {action}")

    st.subheader("Insights")
    insights = _load_insights()
    if not insights:
        st.info("No insights available. Generate them after running Red Team.")
    else:
        for insight in insights:
            with st.expander(f"{insight.id} · {insight.summary} · Confidence {insight.confidence:.2f}"):
                st.write(insight.text)
                st.caption(
                    ", ".join(
                        f"{span.source_id} p{span.page}" for span in insight.provenance
                    )
                )

    st.subheader("Suggested Actions & Next Hypotheses")
    actions = _load_actions()
    if not actions:
        st.info("Generate insights to see suggested actions.")
    else:
        for action in actions:
            label = f"{action.title} · {action.tag}"
            with st.expander(label):
                st.write(action.detail)
                if action.related_claims:
                    st.caption(f"Related claims: {', '.join(action.related_claims)}")


if __name__ == "__main__":
    main()
