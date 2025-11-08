"""Data models for claims, evidence, and insights."""

from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


class EvidenceSpan(BaseModel):
    source_id: str
    page: int
    char_start: int
    char_end: int
    quote: str


class Claim(BaseModel):
    id: str
    topic: str
    text: str
    citations: List[EvidenceSpan] = Field(default_factory=list)
    confidence: Optional[float] = None
    status: Literal["draft", "reviewed"] = "draft"


class ReviewedClaim(Claim):
    verdict: Literal["Supported", "Weak", "Contradicted"]
    reviewer_notes: str = ""


class Insight(BaseModel):
    id: str
    topic: str
    claim_ids: List[str]
    text: str
    confidence: float
    provenance: List[EvidenceSpan]
