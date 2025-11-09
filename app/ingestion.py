"""PDF ingestion pipeline: load PDFs, chunk text, and persist to Chroma."""

from __future__ import annotations

import logging
import os
import re
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List

import fitz

from .utils import configure_logging, ensure_dirs
from .vectorstore import build_embeddings, get_collection, get_collection_name

configure_logging()
logger = logging.getLogger(__name__)

TARGET_TOKENS = 350
CHUNK_OVERLAP = 60
EMBEDDING_BATCH_SIZE = 100
PDF_STAGING_DIR = Path(os.getenv("PDF_STAGING_DIR", "pdf_workspace")).expanduser()
ensure_dirs(PDF_STAGING_DIR)

_TOKEN_PATTERN = re.compile(r"\S+\s*")
_SENTENCE_PATTERN = re.compile(r"(?<=[.!?])\s+")


def load_pdf(path: str) -> List[Dict]:
    pdf_path = Path(path).expanduser().resolve()
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF not found: {pdf_path}")

    doc = fitz.open(str(pdf_path))
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
    return pages


def _split_into_paragraphs(text: str) -> List[tuple[str, int, int]]:
    paragraphs = []
    current_pos = 0
    for line in text.split("\n"):
        line_stripped = line.strip()
        if line_stripped:
            start = text.find(line_stripped, current_pos)
            end = start + len(line_stripped)
            paragraphs.append((line_stripped, start, end))
            current_pos = end
    return paragraphs


def _split_into_sentences(text: str) -> List[tuple[str, int, int]]:
    sentences = []
    current_pos = 0
    parts = _SENTENCE_PATTERN.split(text)
    for part in parts:
        part_stripped = part.strip()
        if part_stripped:
            start = text.find(part_stripped, current_pos)
            end = start + len(part_stripped)
            sentences.append((part_stripped, start, end))
            current_pos = end
    return sentences


def chunk_pages(
    pages: List[Dict],
    target_tokens: int = TARGET_TOKENS,
    overlap: int = CHUNK_OVERLAP,
    use_semantic_boundaries: bool = True,
) -> List[Dict]:
    if overlap >= target_tokens:
        raise ValueError("overlap must be smaller than target_tokens")

    chunks: List[Dict] = []
    for page in pages:
        text = page.get("text", "")
        if not text.strip():
            continue

        if use_semantic_boundaries:
            paragraphs = _split_into_paragraphs(text)
            for para_text, para_start, para_end in paragraphs:
                if not para_text:
                    continue
                sentences = _split_into_sentences(para_text)
                current_chunk_sentences = []
                current_token_count = 0
                chunk_idx = 0

                for sent_text, sent_start_rel, sent_end_rel in sentences:
                    sent_tokens = len(re.findall(_TOKEN_PATTERN, sent_text))
                    if current_token_count + sent_tokens <= target_tokens:
                        current_chunk_sentences.append(
                            (sent_text, para_start + sent_start_rel, para_start + sent_end_rel)
                        )
                        current_token_count += sent_tokens
                    else:
                        if current_chunk_sentences:
                            chunk_text = " ".join(s[0] for s in current_chunk_sentences)
                            chunk_start = current_chunk_sentences[0][1]
                            chunk_end = current_chunk_sentences[-1][2]
                            chunks.append(
                                {
                                    "id": f"{page['source_id']}:p{page['page']:04d}:c{chunk_idx:04d}",
                                    "text": chunk_text,
                                    "source_id": page["source_id"],
                                    "page": page["page"],
                                    "char_start": chunk_start,
                                    "char_end": chunk_end,
                                }
                            )
                            chunk_idx += 1
                            if overlap > 0 and len(current_chunk_sentences) > 1:
                                overlap_count = max(1, (overlap * len(current_chunk_sentences)) // target_tokens)
                                current_chunk_sentences = current_chunk_sentences[-overlap_count:]
                                current_token_count = sum(len(re.findall(_TOKEN_PATTERN, s[0])) for s in current_chunk_sentences)
                            else:
                                current_chunk_sentences = []
                                current_token_count = 0

                        current_chunk_sentences.append(
                            (sent_text, para_start + sent_start_rel, para_start + sent_end_rel)
                        )
                        current_token_count = sent_tokens

                if current_chunk_sentences:
                    chunk_text = " ".join(s[0] for s in current_chunk_sentences)
                    chunk_start = current_chunk_sentences[0][1]
                    chunk_end = current_chunk_sentences[-1][2]
                    chunks.append(
                        {
                            "id": f"{page['source_id']}:p{page['page']:04d}:c{chunk_idx:04d}",
                            "text": chunk_text,
                            "source_id": page["source_id"],
                            "page": page["page"],
                            "char_start": chunk_start,
                            "char_end": chunk_end,
                        }
                    )
        else:
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


def embed_chunks(chunks: List[Dict], batch_size: int = EMBEDDING_BATCH_SIZE) -> int:
    if not chunks:
        logger.warning("No chunks provided for embedding")
        return 0

    collection = get_collection()
    collection_name = get_collection_name()
    total_inserted = 0

    for batch_start in range(0, len(chunks), batch_size):
        batch_end = min(batch_start + batch_size, len(chunks))
        batch = chunks[batch_start:batch_end]
        documents = [chunk["text"] for chunk in batch]
        metadatas = [
            {
                "source_id": chunk["source_id"],
                "page": chunk["page"],
                "char_start": chunk["char_start"],
                "char_end": chunk["char_end"],
            }
            for chunk in batch
        ]
        embeddings = build_embeddings(documents)
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )
        total_inserted += len(batch)
        logger.info(
            "Upserted batch %d-%d (%d chunks total) into '%s'",
            batch_start,
            batch_end - 1,
            total_inserted,
            collection_name,
        )

    logger.info("Completed embedding: %d chunks into collection '%s'", total_inserted, collection_name)
    return total_inserted


def _process_single_pdf(pdf_path: Path) -> tuple[int, str]:
    try:
        pages = load_pdf(str(pdf_path))
        chunks = chunk_pages(pages, use_semantic_boundaries=True)
        inserted = embed_chunks(chunks)
        return inserted, pdf_path.name
    except Exception as exc:
        logger.error("Failed to process %s: %s", pdf_path.name, exc)
        return 0, pdf_path.name


def ingest_dir(input_dir: str | Path, parallel: bool = True, max_workers: int = 4) -> int:
    input_path = Path(input_dir).expanduser().resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"Input directory not found: {input_path}")

    pdf_files = sorted([p for p in input_path.glob("**/*.pdf") if p.is_file()])
    if not pdf_files:
        logger.warning("No PDF files found under %s", input_path)
        return 0

    total_chunks = 0

    if parallel and len(pdf_files) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for inserted, pdf_name in executor.map(_process_single_pdf, pdf_files):
                total_chunks += inserted
                logger.info("Ingested %d chunks from %s (running total: %d)", inserted, pdf_name, total_chunks)
    else:
        for pdf in pdf_files:
            inserted, pdf_name = _process_single_pdf(pdf)
            total_chunks += inserted
            logger.info("Ingested %d chunks from %s (running total: %d)", inserted, pdf_name, total_chunks)

    logger.info("Completed ingestion: %d chunks from %d PDFs", total_chunks, len(pdf_files))
    return total_chunks
