"""
Common Schemas
Shared DTOs used across multiple endpoints
"""
from pydantic import BaseModel
from typing import Optional, List, TypeVar, Generic
from uuid import UUID
from datetime import datetime


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response wrapper"""
    items: List[T]
    total: int
    page: int
    limit: int
    has_more: bool


class ErrorResponse(BaseModel):
    """Standard error response"""
    detail: str
    code: Optional[str] = None
    timestamp: datetime = None

    def __init__(self, **data):
        if 'timestamp' not in data or data['timestamp'] is None:
            data['timestamp'] = datetime.utcnow()
        super().__init__(**data)


class SuccessResponse(BaseModel):
    """Standard success response"""
    success: bool = True
    message: str


class HealthResponse(BaseModel):
    """Health check response"""
    status: str
    version: str
    timestamp: datetime
