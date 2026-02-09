"""
Digest Schemas
Request/Response DTOs for daily digest endpoints
"""
from pydantic import BaseModel


class DigestMemoryItem(BaseModel):
    """Single memory item in the daily digest."""

    id: str
    title: str
    type: str
    summary: str | None = None
    tags: list[str] = []
    created_at: str


class DigestJournalItem(BaseModel):
    """Single journal item in the daily digest."""

    id: str
    mood: str
    preview: str
    created_at: str


class DigestSummary(BaseModel):
    """Aggregate counts for the day."""

    memory_count: int
    journal_count: int
    chat_count: int


class DigestInsights(BaseModel):
    """AI-generated insights for the day."""

    main_topics: list[str]
    suggested_questions: list[str]


class DigestResponse(BaseModel):
    """Full daily digest response."""

    date: str
    summary: DigestSummary
    memories: list[DigestMemoryItem]
    journals: list[DigestJournalItem]
    chats: list[dict]
    insights: DigestInsights
