"""다이어리 도메인 모델 (Pydantic).

Repository → Service → Router로 흐르는 핵심 엔티티.
일기 본문 + 무드 + 태그 등 비즈니스 불변식을 모델 레벨에서 강제한다.

마이그레이션 정책(점진적):
- 핵심 메서드(create/get_by_id/list)는 이 모델을 사용
- 통계/검색/감정 추세 같은 분석성 메서드는 당분간 dict 유지 (caller가 다양함)
  → 운영 데이터로 안정성 검증 후 도메인 모델로 전환
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DiaryEntry(BaseModel):
    """다이어리 항목 도메인 엔티티."""

    model_config = ConfigDict(frozen=False)

    id: UUID
    user_id: UUID
    content: str
    mood: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime | None = None
