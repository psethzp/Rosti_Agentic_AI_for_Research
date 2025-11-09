"""Helpers for caching and retrieving source page text."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Dict, List, Optional

import fitz  # PyMuPDF

from .utils import ensure_dirs

TEXT_CACHE_DIR = Path(os.getenv("TEXT_CACHE_DIR", ".data/page_cache")).expanduser()
ensure_dirs(TEXT_CACHE_DIR)


def cache_page_texts(source_id: str, pages: List[Dict]) -> Path:
    """Persist raw page text for later validation."""
    payload = [
        {"page": page["page"], "text": page.get("text", "")}
        for page in pages
        if page.get("text")
    ]
    target = TEXT_CACHE_DIR / f"{source_id}.json"
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def cache_single_page_text(source_id: str, page: int, text: str) -> Path:
    """Insert or update one page entry in the cache."""
    target = TEXT_CACHE_DIR / f"{source_id}.json"
    payload: List[Dict] = []
    if target.exists():
        try:
            payload = json.loads(target.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            payload = []
    updated = False
    for entry in payload:
        if entry.get("page") == page:
            entry["text"] = text
            updated = True
            break
    if not updated:
        payload.append({"page": page, "text": text})
        payload.sort(key=lambda item: item.get("page", 0))
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target


def load_page_text(source_id: str, page: int) -> Optional[str]:
    """Return the cached text for a given source/page if available."""
    path = TEXT_CACHE_DIR / f"{source_id}.json"
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    for entry in data:
        if entry.get("page") == page:
            return entry.get("text")
    return None


def extract_page_text_from_pdf(pdf_path: Path, page: int) -> Optional[str]:
    """Read a specific page from a PDF on demand."""
    if page < 1:
        return None
    try:
        doc = fitz.open(str(pdf_path))
    except Exception:  # noqa: BLE001
        return None
    try:
        if page > doc.page_count:
            return None
        text = doc.load_page(page - 1).get_text("text").strip()
        return text or None
    finally:
        doc.close()
