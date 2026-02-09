"""
Journal Schemas
Request/Response DTOs for journal endpoints
"""
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class JournalCreate(BaseModel):
    """Request to create a new journal entry."""

    content: str


class JournalResponse(BaseModel):
    """Single journal entry response."""

    id: UUID
    content: str
    mood: str | None = None
    created_at: str
    updated_at: str


class ReviewRequest(BaseModel):
    """Request body for review questions and insight analysis."""

    content: str


class ReviewQuestionsResponse(BaseModel):
    """Response containing generated review questions."""

    questions: list[str]


class InsightsResponse(BaseModel):
    """Response containing cognitive distortion analysis."""

    has_distortions: bool
    distortions: list[dict[str, Any]]
    wellness_score: int


class RelatedMemoryItem(BaseModel):
    """Single related memory item in the sidebar."""

    id: str | None = None
    title: str
    summary: str
    type: str
    created_at: str | None = None
    similarity: float


class RelatedMemoriesResponse(BaseModel):
    """Response containing related memories for the context sidebar."""

    memories: list[RelatedMemoryItem]


class GenerateDraftRequest(BaseModel):
    """Request to generate a journal draft from an evening chat session."""

    session_id: UUID


class GenerateDraftResponse(BaseModel):
    """Response containing the AI-generated journal draft."""

    draft: str
    session_id: UUID
