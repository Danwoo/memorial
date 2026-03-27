from typing import Any
from uuid import UUID

from pydantic import BaseModel


class DiaryCreate(BaseModel):
    """일기 항목 생성 요청."""

    content: str
    scrap_ids: list[str] | None = None


class DiaryUpdate(BaseModel):
    """일기 항목 수정 요청."""

    content: str
    scrap_ids: list[str] | None = None


class DiaryResponse(BaseModel):
    """일기 항목 응답."""

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


class RelatedScrapItem(BaseModel):
    """사이드바용 관련 스크랩 항목."""

    id: str | None = None
    title: str
    summary: str
    type: str
    created_at: str | None = None
    similarity: float


class RelatedScrapsResponse(BaseModel):
    """컨텍스트 사이드바용 관련 스크랩 응답."""

    scraps: list[RelatedScrapItem]


class GenerateDraftRequest(BaseModel):
    """저녁 대화 세션에서 일기 초안 생성 요청."""

    session_id: UUID


class GenerateDraftResponse(BaseModel):
    """AI 생성 일기 초안 응답."""

    draft: str
    session_id: UUID


class DiaryDateInfo(BaseModel):
    """일기 존재 날짜 정보."""

    date: str
    count: int
    mood: str | None = None
    tags: list[str] = []


class DiaryDatesResponse(BaseModel):
    """일기 날짜 목록 응답."""

    dates: list[DiaryDateInfo]


class LinkedDiaryItem(BaseModel):
    """스크랩에 연결된 일기 항목."""

    diary_id: str
    date: str
    preview: str
    mood: str | None = None
    link_type: str = "manual"


class LinkedDiariesResponse(BaseModel):
    """스크랩 역참조 일기 목록 응답."""

    diaries: list[LinkedDiaryItem]
