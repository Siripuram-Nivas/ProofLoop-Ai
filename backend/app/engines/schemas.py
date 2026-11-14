"""Validated contracts returned by AI providers.

These models are also the JSON schemas sent to OpenAI Structured Outputs and
Gemini response_schema, so keep them free of unsupported JSON Schema features.
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

Stance = Literal["supports", "contradicts", "insufficient"]
RecommendedVerdict = Literal[
    "supported", "contradicted", "mixed", "insufficient", "unverified"
]


class ExtractedClaim(BaseModel):
    text: str = Field(min_length=8, max_length=600)
    category: str = Field(default="general", max_length=40)
    confidence: float = Field(default=0.6, ge=0, le=1)


class ClaimExtraction(BaseModel):
    claims: list[ExtractedClaim] = Field(default_factory=list, max_length=8)


class EvidenceNote(BaseModel):
    source_url: str = Field(min_length=8, max_length=2000)
    stance: Stance
    relevance: float = Field(default=0.5, ge=0, le=1)
    rationale: str = Field(min_length=4, max_length=800)


class EvidenceAnalysis(BaseModel):
    claim_text: str = Field(min_length=4, max_length=600)
    notes: list[EvidenceNote] = Field(default_factory=list, max_length=12)


class ClaimReview(BaseModel):
    claim_text: str = Field(min_length=4, max_length=600)
    recommended_verdict: RecommendedVerdict
    confidence: float = Field(default=0.5, ge=0, le=1)
    concerns: list[str] = Field(default_factory=list, max_length=8)
    reasoning: str = Field(min_length=4, max_length=1200)


class SearchSource(BaseModel):
    url: str
    title: Optional[str] = None
    publisher: Optional[str] = None
    published_at: Optional[str] = None
    retrieved_at: str
    excerpt: Optional[str] = None
    locator: Optional[str] = None
    accessible: bool = False
    note: Optional[str] = None
    provenance: dict[str, Any] = Field(default_factory=dict)


class SearchDiscovery(BaseModel):
    queries: list[str] = Field(default_factory=list)
    sources: list[SearchSource] = Field(default_factory=list)
    invalid_sources: int = 0
    grounding: dict[str, Any] = Field(default_factory=dict)
    usage: dict[str, Any] = Field(default_factory=dict)
