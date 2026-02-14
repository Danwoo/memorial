from typing import Any
from uuid import UUID

from pydantic import BaseModel


class JournalCreate(BaseModel):
    """저널 항목 생성 요청."""

    content: str
    memory_ids: list[str] | None = None


class JournalResponse(BaseModel):
    """저널 항목 응답."""

    id: UUID
    content: str
    mood: str | None = None
    created_at: str
    updated_at: str


class ReviewRequest(BaseModel):
    """성찰 질문 및 인사이트 분석 요청."""

    content: str


class ReviewQuestionsResponse(BaseModel):
    """생성된 성찰 질문 응답."""

    questions: list[str]


class InsightsResponse(BaseModel):
    """인지 왜곡 분석 결과 응답."""

    has_distortions: bool
    distortions: list[dict[str, Any]]
    wellness_score: int


class RelatedMemoryItem(BaseModel):
    """사이드바용 관련 메모리 항목."""

    id: str | None = None
    title: str
    summary: str
    type: str
    created_at: str | None = None
    similarity: float


class RelatedMemoriesResponse(BaseModel):
    """컨텍스트 사이드바용 관련 메모리 응답."""

    memories: list[RelatedMemoryItem]


class GenerateDraftRequest(BaseModel):
    """저녁 대화 세션에서 저널 초안 생성 요청."""

    session_id: UUID


class GenerateDraftResponse(BaseModel):
    """AI 생성 저널 초안 응답."""

    draft: str
    session_id: UUID


class JournalDateInfo(BaseModel):
    """저널 존재 날짜 정보."""

    date: str
    count: int
    mood: str | None = None


class JournalDatesResponse(BaseModel):
    """저널 날짜 목록 응답."""

    dates: list[JournalDateInfo]


class LinkedJournalItem(BaseModel):
    """메모리에 연결된 저널 항목."""

    journal_id: str
    date: str
    preview: str
    mood: str | None = None
    link_type: str = "manual"


class LinkedJournalsResponse(BaseModel):
    """메모리 역참조 저널 목록 응답."""

    journals: list[LinkedJournalItem]
