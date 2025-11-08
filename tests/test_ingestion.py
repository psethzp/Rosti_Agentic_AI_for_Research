"""Ingestion module tests."""

from __future__ import annotations

import shutil
import sys
from pathlib import Path

import chromadb
from chromadb.config import Settings
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import ingestion  # noqa: E402


SAMPLE_PDF = Path("docs/sample.pdf")


@pytest.fixture(scope="module")
def sample_pdf() -> Path:
    assert SAMPLE_PDF.exists(), "Sample PDF missing"
    return SAMPLE_PDF


def test_load_and_chunk(sample_pdf: Path) -> None:
    pages = ingestion.load_pdf(str(sample_pdf))
    assert pages, "Expected at least one page"
    assert pages[0]["text"], "Page text should not be empty"
    chunks = ingestion.chunk_pages(pages, target_tokens=50, overlap=10)
    assert chunks, "Chunking should yield data"
    chunk = chunks[0]
    for key in ("id", "text", "source_id", "page", "char_start", "char_end"):
        assert key in chunk
    assert chunk["char_start"] >= 0
    assert chunk["char_end"] > chunk["char_start"]


def test_embed_chunks(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sample_pdf: Path) -> None:
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma"))
    pages = ingestion.load_pdf(str(sample_pdf))
    chunks = ingestion.chunk_pages(pages, target_tokens=50, overlap=10)
    inserted = ingestion.embed_chunks(chunks)
    assert inserted == len(chunks)
    client = chromadb.PersistentClient(
        path=str(tmp_path / "chroma"),
        settings=Settings(anonymized_telemetry=False),
    )
    collection = client.get_or_create_collection("docs")
    assert collection.count() >= len(chunks)


def test_ingest_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, sample_pdf: Path) -> None:
    monkeypatch.setenv("CHROMA_DIR", str(tmp_path / "chroma2"))
    ingest_root = tmp_path / "pdfs"
    ingest_root.mkdir()
    shutil.copy(sample_pdf, ingest_root / sample_pdf.name)
    total = ingestion.ingest_dir(ingest_root)
    assert total > 0
