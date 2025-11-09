from __future__ import annotations

import asyncio
import json
import os
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Protocol

from .agents import (
    run_action_planner,
    run_red_team,
    run_researcher,
    run_reviewer,
    run_synthesizer,
)
from .ingestion import ingest_dir
from .schemas import ReviewedClaim

RUNS_DIR = Path(os.getenv("RUNS_DIR", "runs")).expanduser()
RUNS_DIR.mkdir(parents=True, exist_ok=True)

PIPELINE_STAGES = ["ingestion", "researcher", "red_team", "synthesizer"]


@dataclass
class RunRecord:
    id: str
    prompt: str
    workspace: Path
    pdf_dir: Path
    artifacts_dir: Path
    chroma_dir: Path
    stage_tracker: Dict[str, str] = field(
        default_factory=lambda: {stage: "pending" for stage in PIPELINE_STAGES}
    )
    status: str = "pending"
    error: Optional[str] = None
    payload: Optional[dict] = None
    source_map: Dict[str, str] = field(default_factory=dict)
    event_queue: asyncio.Queue[str] = field(default_factory=asyncio.Queue)


_RUNS: Dict[str, RunRecord] = {}


class EnvPatcher:
    def __init__(self, **updates: str) -> None:
        self.updates = updates
        self.previous: Dict[str, Optional[str]] = {}

    def __enter__(self) -> None:
        for key, value in self.updates.items():
            self.previous[key] = os.environ.get(key)
            os.environ[key] = value

    def __exit__(self, exc_type, exc, tb) -> None:
        for key, old in self.previous.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old if isinstance(old, str) else old


def _queue_payload(run: RunRecord, event: str, data: str) -> None:
    payload = f"event: {event}\ndata: {data}\n\n"
    run.event_queue.put_nowait(payload)


def _queue_json(run: RunRecord, event: str, data: dict) -> None:
    _queue_payload(run, event, json.dumps(data))


def _queue_message(run: RunRecord, html: str) -> None:
    _queue_payload(run, "message", html)


def _set_stage(run: RunRecord, stage: str, status: str, message: str) -> None:
    if stage in run.stage_tracker:
        run.stage_tracker[stage] = status
    _queue_json(
        run,
        "stage",
        {
            "stage": stage,
            "status": status,
            "message": message,
            "tracker": run.stage_tracker,
        },
    )
    _queue_message(run, f"<div>{message}</div>")


def create_run(prompt: str) -> RunRecord:
    run_id = str(uuid.uuid4())
    workspace = RUNS_DIR / run_id
    pdf_dir = workspace / "pdfs"
    artifacts_dir = workspace / "artifacts"
    chroma_dir = workspace / "chroma"
    for path in (workspace, pdf_dir, artifacts_dir, chroma_dir):
        path.mkdir(parents=True, exist_ok=True)
    run = RunRecord(
        id=run_id,
        prompt=prompt,
        workspace=workspace,
        pdf_dir=pdf_dir,
        artifacts_dir=artifacts_dir,
        chroma_dir=chroma_dir,
    )
    _RUNS[run_id] = run
    return run


async def save_uploaded_files(run: RunRecord, files: Iterable["UploadFileLike"]) -> List[str]:
    saved: List[str] = []
    for file in files:
        if not file.filename:
            continue
        safe_name = Path(file.filename).name
        target = run.pdf_dir / safe_name
        content = await file.read()
        target.write_bytes(content)
        source_id = Path(safe_name).stem
        run.source_map[source_id] = safe_name
        saved.append(safe_name)
    return saved


def get_run(run_id: str) -> Optional[RunRecord]:
    return _RUNS.get(run_id)


def start_run(run: RunRecord) -> None:
    run.status = "running"
    asyncio.create_task(_execute_run(run))


async def event_stream(run: RunRecord):
    yield "retry: 2000\n\n"
    while True:
        payload = await run.event_queue.get()
        yield payload


async def _execute_run(run: RunRecord) -> None:
    try:
        env = EnvPatcher(
            ARTIFACTS_DIR=str(run.artifacts_dir),
            PDF_STAGING_DIR=str(run.pdf_dir),
            CHROMA_DIR=str(run.chroma_dir),
        )
        with env:
            await _maybe_ingest(run)
            reviewed = await asyncio.to_thread(_run_claim_pipeline, run)
            findings = await asyncio.to_thread(_run_red_team, run, reviewed)
            await asyncio.to_thread(_run_synthesis, run, reviewed, findings)
        run.payload = _build_payload(run)
        run.status = "completed"
        _queue_json(run, "completed", {"run_id": run.id})
        _queue_message(run, "<div><strong>Run completed.</strong></div>")
    except Exception as exc:  # noqa: BLE001
        run.status = "failed"
        run.error = str(exc)
        _queue_json(run, "failed", {"error": str(exc)})
        _queue_message(run, f"<div class='text-red-500'>Error: {exc}</div>")


async def _maybe_ingest(run: RunRecord) -> None:
    files = list(run.pdf_dir.glob("*.pdf"))
    if not files:
        _set_stage(run, "ingestion", "done", "No PDFs uploaded; skipping ingestion.")
        return
    _set_stage(run, "ingestion", "running", "Ingesting uploaded PDFs…")
    await asyncio.to_thread(ingest_dir, run.pdf_dir)
    _set_stage(run, "ingestion", "done", "Ingestion completed.")


def _run_claim_pipeline(run: RunRecord) -> List[ReviewedClaim]:
    _set_stage(run, "researcher", "running", "Running Researcher agent…")
    claims = run_researcher(run.prompt)
    reviewed = run_reviewer(claims)
    _set_stage(run, "researcher", "done", f"Researcher produced {len(reviewed)} claims.")
    return reviewed


def _run_red_team(run: RunRecord, reviewed: List[ReviewedClaim]):
    _set_stage(run, "red_team", "running", "Running Red Team agent…")
    findings = run_red_team(run.prompt, reviewed)
    _set_stage(run, "red_team", "done", f"Red Team generated {len(findings)} findings.")
    return findings


def _run_synthesis(run: RunRecord, reviewed: List[ReviewedClaim], findings):
    _set_stage(run, "synthesizer", "running", "Synthesizing insights and actions…")
    insights = run_synthesizer(run.prompt, reviewed, findings)
    actions = run_action_planner(run.prompt, reviewed, insights)
    _set_stage(
        run,
        "synthesizer",
        "done",
        f"Generated {len(insights)} insights & {len(actions)} actions.",
    )


def _load_json(path: Path, default):
    if not path.exists():
        return default
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return default


def _build_payload(run: RunRecord) -> dict:
    artifacts = run.artifacts_dir
    claims_raw = _load_json(artifacts / "claims_reviewed.json", [])
    report_raw = _load_json(artifacts / "report.json", {})
    challenges = _load_json(artifacts / "challenges.json", [])
    actions = _load_json(artifacts / "actions.json", [])

    claims_index = {claim["id"]: claim for claim in claims_raw}

    insights = report_raw.get("insights", []) if isinstance(report_raw, dict) else report_raw
    for insight in insights:
        claim_ids = insight.get("claim_ids", [])
        insight["claims"] = [claims_index[cid] for cid in claim_ids if cid in claims_index]
        insight["topic"] = _derive_topic(
            candidate=insight.get("topic"),
            summary=insight.get("summary"),
            fallback_claims=insight["claims"],
            prompt=run.prompt,
        )
        insight["summary"] = _derive_summary(insight.get("summary"), insight.get("text"))

    for finding in challenges:
        finding["topic"] = _derive_topic(
            candidate=finding.get("topic"),
            summary=finding.get("summary"),
            fallback_claims=[claims_index.get(finding.get("claim_id"))] if finding.get("claim_id") else [],
            prompt=run.prompt,
        )
        finding["summary"] = _derive_summary(finding.get("summary"), finding.get("detail"))

    payload = {
        "insights": insights,
        "challenges": challenges,
        "actions": actions,
        "pdfs": [
            {"source_id": source_id, "filename": filename}
            for source_id, filename in run.source_map.items()
        ],
    }
    return payload


def _derive_topic(
    candidate: Optional[str],
    summary: Optional[str],
    fallback_claims: List[dict],
    prompt: str,
) -> str:
    text = candidate or summary or _first_claim_text(fallback_claims) or "Insight"
    if text.strip().lower() == prompt.strip().lower():
        text = summary or _first_claim_text(fallback_claims) or "Insight"
    return text.strip()


def _derive_summary(summary: Optional[str], detail: Optional[str]) -> str:
    if summary and summary.strip():
        return summary.strip()
    if detail and detail.strip():
        first_sentence = detail.split(".")[0].strip()
        return first_sentence or detail.strip()
    return ""


def _first_claim_text(claims: List[dict]) -> Optional[str]:
    for claim in claims or []:
        text = claim.get("summary") or claim.get("text")
        if text:
            return text
    return None


# Typing helper for UploadFile-like objects
class UploadFileLike(Protocol):
    filename: str

    async def read(self) -> bytes:
        ...
