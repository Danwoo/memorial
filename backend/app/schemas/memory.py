"""
Pydantic Schemas for Memory (지식 저장소)
API Request/Response DTOs - Based on API_Spec.md
"""
from pydantic import BaseModel, Field, HttpUrl
from typing import Optional, List, Literal
from datetime import datetime
from uuid import UUID


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
    url: Optional[str] = None  # Required for WEB/PDF
    content: Optional[str] = None  # Required for NOTE
    memo: Optional[str] = None  # User's initial thought
    
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
    summary: Optional[str] = None
    source_type: SourceType
    created_at: datetime
    
    class Config:
        from_attributes = True


class MemoryListResponse(BaseModel):
    """GET /memories - Response"""
    items: List[MemoryListItem]
    total: int


class MemoryDetail(BaseModel):
    """GET /memories/{id} - Response"""
    id: UUID
    title: str
    content: str
    summary: Optional[str] = None
    source_url: Optional[str] = None
    source_type: SourceType
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
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
    summary: Optional[str] = None
    source_url: Optional[str] = None
    source_type: SourceType
    status: MemoryStatus = "pending"
    tags: Optional[List[str]] = None
    created_at: datetime
    updated_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True
