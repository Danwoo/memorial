from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

SourceType = Literal["WEB", "PDF", "NOTE", "KAKAO", "CHAT_HISTORY", "JOURNAL"]
MemoryStatus = Literal["pending", "processing", "completed", "failed"]


# --- 요청 스키마 ---


class MemoryCreate(BaseModel):
    """메모리 생성 요청."""

    source_type: SourceType = Field(alias="sourceType")
    url: str | None = None
    content: str | None = None
    memo: str | None = None

    class Config:
        populate_by_name = True


# --- 응답 스키마 ---


class MemoryCreateResponse(BaseModel):
    """메모리 생성 응답."""

    id: UUID
    status: MemoryStatus = "processing"


class MemoryListItem(BaseModel):
    """메모리 목록 항목."""

    id: UUID
    title: str
    summary: str | None = None
    source_type: SourceType
    created_at: datetime

    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    """메모리 목록 응답."""

    items: list[MemoryListItem]
    total: int


class MemoryDetail(BaseModel):
    """메모리 상세 응답."""

    id: UUID
    title: str
    content: str
    summary: str | None = None
    source_url: str | None = None
    source_type: SourceType
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True


# --- 내부 스키마 (서비스 레이어용) ---


class MemoryInDB(BaseModel):
    """DB 행 표현."""

    id: UUID
    user_id: UUID
    title: str
    content: str
    summary: str | None = None
    source_url: str | None = None
    source_type: SourceType
    status: MemoryStatus = "pending"
    tags: list[str] | None = None
    created_at: datetime
    updated_at: datetime | None = None

    class Config:
        from_attributes = True
