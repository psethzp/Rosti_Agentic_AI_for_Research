"""Streamlit UI for Collective Insight Lab."""

from __future__ import annotations

import json
import os
import shutil
import sys
import tempfile
from pathlib import Path
from typing import List

import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.agents import (  # type: ignore  # noqa: E402
    load_claims_from_artifacts,
    reset_artifacts,
    run_researcher,
    run_reviewer,
    run_synthesizer,
)
from app.graph import build_reasoning_graph  # type: ignore  # noqa: E402
from app.ingestion import ingest_dir  # type: ignore  # noqa: E402
from app.schemas import Insight, ReviewedClaim  # type: ignore  # noqa: E402
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
    return [Insight.model_validate(entry) for entry in data]


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
        run_researcher_btn = st.button("Run Researcher")
        run_reviewer_btn = st.button("Run Reviewer + Synthesizer")

    if run_researcher_btn:
        if not topic.strip():
            st.error("Please enter a topic before running the Researcher.")
        else:
            with st.spinner("Generating claims..."):
                run_researcher(topic)
            st.success("Researcher finished. Check artifacts/claims.json.")

    if run_reviewer_btn:
        try:
            claims = load_claims_from_artifacts()
        except FileNotFoundError:
            st.error("claims.json not found. Run the Researcher first.")
        else:
            current_topic = topic or (claims[0].topic if claims else "Untitled Topic")
            with st.spinner("Reviewing claims and synthesizing insights..."):
                reviewed = run_reviewer(claims)
                insights = run_synthesizer(current_topic, reviewed)
            if insights:
                st.success("Reviewer + Synthesizer finished. Check artifacts folder.")
            else:
                st.warning("Reviewer finished but no insights were produced. Verify claim verdicts.")

    st.subheader("Reasoning Graph")
    st.graphviz_chart(build_reasoning_graph(include_red_team=True))

    st.subheader("Insights")
    insights = _load_insights()
    if not insights:
        st.info("No insights available. Run the pipeline to generate them.")
    else:
        for insight in insights:
            with st.expander(f"{insight.id} · Confidence {insight.confidence:.2f}"):
                st.write(insight.text)
                st.caption(
                    ", ".join(
                        f"{span.source_id} p{span.page}" for span in insight.provenance
                    )
                )

    st.subheader("Reviewed Claims")
    reviewed_claims = _load_reviewed_claims()
    if reviewed_claims:
        st.dataframe(
            [
                {
                    "ID": claim.id,
                    "Text": claim.text,
                    "Verdict": claim.verdict,
                    "Notes": claim.reviewer_notes,
                    "Citation": (
                        f"{claim.citations[0].source_id} p{claim.citations[0].page}"
                        if claim.citations
                        else "N/A"
                    ),
                }
                for claim in reviewed_claims
            ]
        )


if __name__ == "__main__":
    main()
