"""Retrieval and researcher agent tests."""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import agents, ingestion, retrieval  # noqa: E402

SAMPLE_PDF = Path("docs/sample.pdf")


@pytest.fixture()
def sample_corpus(tmp_path: Path) -> Path:
    ingest_root = tmp_path / "pdfs"
    ingest_root.mkdir()
    shutil.copy(SAMPLE_PDF, ingest_root / SAMPLE_PDF.name)
    return ingest_root


def test_search_returns_ranked_hits(monkeypatch: pytest.MonkeyPatch, sample_corpus: Path) -> None:
    chroma_dir = sample_corpus.parent / "chroma-search"
    monkeypatch.setenv("CHROMA_DIR", str(chroma_dir))
    ingestion.ingest_dir(sample_corpus)
    results = retrieval.search("Collective Insight sample", k=3)
    assert results, "search should return at least one result"
    top = results[0]
    assert top["text"]
    assert top["source_id"] == SAMPLE_PDF.stem
    assert isinstance(top["score"], float)


def test_run_researcher_creates_claims(monkeypatch: pytest.MonkeyPatch, sample_corpus: Path) -> None:
    chroma_dir = sample_corpus.parent / "chroma-researcher"
    artifacts_dir = sample_corpus.parent / "artifacts"
    monkeypatch.setenv("CHROMA_DIR", str(chroma_dir))
    monkeypatch.setenv("ARTIFACTS_DIR", str(artifacts_dir))
    ingestion.ingest_dir(sample_corpus)
    claims = agents.run_researcher("Collective Insight sample topic")
    assert len(claims) >= 3
    artifact_path = artifacts_dir / "claims.json"
    assert artifact_path.exists()
    saved = json.loads(artifact_path.read_text(encoding="utf-8"))
    assert len(saved) == len(claims)
    pages = ingestion.load_pdf(str(SAMPLE_PDF))
    page_lookup = {page["page"]: page["text"] for page in pages}
    for claim in claims:
        assert claim.citations, "Each claim should include at least one citation"
        span = claim.citations[0]
        page_text = page_lookup.get(span.page, "")
        assert span.quote.strip() in page_text
