"""Trace logging utilities for agent orchestration."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import ensure_dirs

TRACE_PATH = Path(os.getenv("TRACE_PATH", "artifacts/traces.jsonl")).expanduser()


def log_trace_event(
    agent: str,
    stage: str,
    topic: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Append a structured trace event for downstream visualizations."""
    payload: Dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "agent": agent,
        "stage": stage,
        "topic": topic,
    }
    if details:
        payload["details"] = details
    ensure_dirs(TRACE_PATH.parent)
    TRACE_PATH.write_text("", encoding="utf-8") if not TRACE_PATH.exists() else None
    with TRACE_PATH.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload) + "\n")
