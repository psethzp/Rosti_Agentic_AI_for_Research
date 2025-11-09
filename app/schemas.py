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
    chunk_id: Optional[str] = None
    chunk_text: Optional[str] = None


class Claim(BaseModel):
    id: str
    topic: str
    summary: Optional[str] = None
    text: str
    subpoints: List[str] = Field(default_factory=list)
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
    summary: str
    text: str
    confidence: float
    provenance: List[EvidenceSpan]


class ActionItem(BaseModel):
    id: str
    topic: str
    title: str
    detail: str
    tag: Literal["Hypothesis", "NextStep", "Clarification"]
    related_claims: List[str] = Field(default_factory=list)


class RedTeamFinding(BaseModel):
    id: str
    topic: str
    claim_id: str
    claim_text: str
    summary: str
    detail: str
    evidence: List[EvidenceSpan]
    severity: Literal["High", "Medium", "Low"] = "Medium"
    actions: List[str] = Field(default_factory=list)
