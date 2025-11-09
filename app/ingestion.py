"""PDF ingestion pipeline: load PDFs, chunk text, and persist to Chroma."""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Dict, List

import fitz  # PyMuPDF

from chromadb.errors import InvalidDimensionException

from .storage import cache_page_texts
from .utils import configure_logging, ensure_dirs
from .vectorstore import (
    build_embeddings,
    get_collection,
    get_collection_name,
    reset_vector_store,
)

configure_logging()
logger = logging.getLogger(__name__)

TARGET_TOKENS = 350
CHUNK_OVERLAP = 60
PDF_STAGING_DIR = Path(os.getenv("PDF_STAGING_DIR", "pdf_workspace")).expanduser()
ensure_dirs(PDF_STAGING_DIR)


def load_pdf(path: str) -> List[Dict]:
    """Return list of page dictionaries extracted from `path`."""
    pdf_path = Path(path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    try:
        doc = fitz.open(str(pdf_path))
    except Exception as exc:
        logger.error("Failed to open %s: %s", pdf_path.name, exc)
        return []
    source_id = pdf_path.stem
    pages: List[Dict] = []
    for page_num in range(doc.page_count):
        page = doc.load_page(page_num)
        text = page.get_text("text").strip()
        pages.append(
            {
                "source_id": source_id,
                "page": page_num + 1,
                "text": text,
                "char_start": 0,
                "char_end": len(text),
            }
        )
    doc.close()
    logger.info("Loaded %s (%d pages)", pdf_path.name, len(pages))
    cache_page_texts(source_id, pages)
    return pages


_TOKEN_PATTERN = re.compile(r"\S+\s*")


def chunk_pages(
    pages: List[Dict], target_tokens: int = TARGET_TOKENS, overlap: int = CHUNK_OVERLAP
) -> List[Dict]:
    """Chunk pages using a greedy token window with overlap."""
    if overlap >= target_tokens:
        raise ValueError("overlap must be smaller than target_tokens")

    chunks: List[Dict] = []
    for page in pages:
        text = page.get("text", "")
        if not text.strip():
            continue
        tokens = [
            {"text": match.group(), "start": match.start(), "end": match.end()}
            for match in _TOKEN_PATTERN.finditer(text)
        ]
        if not tokens:
            continue
        start_idx = 0
        chunk_idx = 0
        token_count = len(tokens)
        while start_idx < token_count:
            end_idx = min(start_idx + target_tokens, token_count)
            chunk_tokens = tokens[start_idx:end_idx]
            chunk_text = "".join(tok["text"] for tok in chunk_tokens).strip()
            if not chunk_text:
                break
            chunks.append(
                {
                    "id": f"{page['source_id']}:p{page['page']:04d}:c{chunk_idx:04d}",
                    "text": chunk_text,
                    "source_id": page["source_id"],
                    "page": page["page"],
                    "char_start": chunk_tokens[0]["start"],
                    "char_end": chunk_tokens[-1]["end"],
                }
            )
            chunk_idx += 1
            if end_idx >= token_count:
                break
            start_idx = max(end_idx - overlap, 0)
            if start_idx == end_idx:
                start_idx += 1
    logger.info("Created %d chunks", len(chunks))
    return chunks


def embed_chunks(chunks: List[Dict]) -> int:
    """Upsert chunk data into Chroma and return number of inserted chunks."""
    if not chunks:
        logger.warning("No chunks provided for embedding")
        return 0
    collection = get_collection()
    documents = [chunk["text"] for chunk in chunks]
    metadatas = [
        {
            "source_id": chunk["source_id"],
            "page": chunk["page"],
            "char_start": chunk["char_start"],
            "char_end": chunk["char_end"],
        }
        for chunk in chunks
    ]
    embeddings = build_embeddings(documents)
    collection_name = get_collection_name()
    try:
        collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
    except InvalidDimensionException:
        logger.warning(
            "Detected embedding dimension mismatch; resetting vector store and retrying."
        )
        reset_vector_store()
        collection = get_collection()
        collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
    logger.info("Upserted %d chunks into collection '%s'", len(chunks), collection_name)
    return len(chunks)


def ingest_dir(input_dir: str | Path) -> int:
    """Walk PDFs inside a directory and ingest them into the vector store."""
    input_path = Path(input_dir).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_path}")

    pdf_files = sorted([p for p in input_path.glob("**/*.pdf") if p.is_file()])
    if not pdf_files:
        logger.warning("No PDF files found under %s", input_path)
        return 0

    total_chunks = 0
    for idx, pdf in enumerate(pdf_files):
        pages = load_pdf(str(pdf))
        chunks = chunk_pages(pages)
        inserted = embed_chunks(chunks)
        total_chunks += inserted
        logger.info(
            "Ingested %d chunks from %s (running total: %d)", inserted, pdf.name, total_chunks
        )
        if idx < len(pdf_files) - 1:
            time.sleep(2)

    logger.info("Completed ingestion: %d chunks from %d PDFs", total_chunks, len(pdf_files))
    return total_chunks
