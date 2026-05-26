from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

SourceType = Literal["WEB", "PDF", "NOTE", "KAKAO", "CHAT_HISTORY", "JOURNAL"]
ScrapStatus = Literal["pending", "processing", "completed", "failed"]


# --- 요청 스키마 ---


class ScrapCreate(BaseModel):
    """스크랩 생성 요청."""

    model_config = ConfigDict(populate_by_name=True)

    source_type: SourceType = Field(alias="sourceType")
    url: str | None = Field(None, max_length=2048)
    content: str | None = Field(None, max_length=50000)
    memo: str | None = Field(None, max_length=5000)


class ScrapUpdate(BaseModel):
    """스크랩 수정 요청. 전달된 필드만 업데이트."""

    title: str | None = Field(None, max_length=200)
    summary: str | None = Field(None, max_length=2000)
    tags: list[str] | None = Field(None, max_length=20)


BulkActionType = Literal["delete", "add_tags", "remove_tags"]


class BulkActionRequest(BaseModel):
    """스크랩 일괄 작업 요청."""

    action: BulkActionType
    scrap_ids: list[UUID] = Field(..., min_length=1, max_length=50)
    tags: list[str] | None = None


class BulkActionResponse(BaseModel):
    """스크랩 일괄 작업 응답."""

    affected: int


# --- 응답 스키마 ---


class ScrapCreateResponse(BaseModel):
    """스크랩 생성 응답."""

    id: UUID
    status: ScrapStatus = "processing"


class ScrapListItem(BaseModel):
    """스크랩 목록 항목."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    summary: str | None = None
    source_type: SourceType
    tags: list[str] = []
    created_at: datetime


class ScrapListResponse(BaseModel):
    """스크랩 목록 응답."""

    items: list[ScrapListItem]
    total: int


class ScrapDetail(BaseModel):
    """스크랩 상세 응답."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    content: str
    summary: str | None = None
    source_url: str | None = None
    source_type: SourceType
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime | None = None


# --- 내부 스키마 (서비스 레이어용) ---


class ScrapInDB(BaseModel):
    """DB 행 표현."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    title: str
    content: str
    summary: str | None = None
    source_url: str | None = None
    source_type: SourceType
    status: ScrapStatus = "pending"
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime | None = None
