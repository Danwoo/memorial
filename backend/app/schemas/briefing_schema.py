from pydantic import BaseModel


class BriefingTodayMemories(BaseModel):
    """오늘 수집된 메모리 요약."""

    count: int
    topics: list[str]


class BriefingStreak(BaseModel):
    """저널 스트릭 간략 정보."""

    current: int
    longest: int


class BriefingResponse(BaseModel):
    """오늘의 브리핑 통합 응답."""

    today_memories: BriefingTodayMemories
    unreviewed_count: int
    streak: BriefingStreak
    suggested_question: str
    connection_hint: str | None = None
