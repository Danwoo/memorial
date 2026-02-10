"""
Pydantic Schemas for Memory (지식 저장소)
API Request/Response DTOs - Based on API_Spec.md
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field

# ========================================
# Enums
# ========================================
SourceType = Literal["WEB", "PDF", "NOTE", "KAKAO", "CHAT_HISTORY", "JOURNAL"]
MemoryStatus = Literal["pending", "processing", "completed", "failed"]


# ========================================
# Request Schemas
# ========================================
class MemoryCreate(BaseModel):
    """POST /memories - Request Body"""

    source_type: SourceType = Field(alias="sourceType")
    url: str | None = None  # Required for WEB/PDF
    content: str | None = None  # Required for NOTE
    memo: str | None = None  # User's initial thought

    class Config:
        populate_by_name = True


# ========================================
# Response Schemas
# ========================================
class MemoryCreateResponse(BaseModel):
    """POST /memories - Response"""

    id: UUID
    status: MemoryStatus = "processing"


class MemoryListItem(BaseModel):
    """GET /memories - List Item"""

    id: UUID
    title: str
    summary: str | None = None
    source_type: SourceType
    created_at: datetime

    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    """GET /memories - Response"""

    items: list[MemoryListItem]
    total: int


class MemoryDetail(BaseModel):
    """GET /memories/{id} - Response"""

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


# ========================================
# Internal Schemas (for Service Layer)
# ========================================
class MemoryInDB(BaseModel):
    """Database row representation"""

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
