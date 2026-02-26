from pydantic import BaseModel


class DigestScrapItem(BaseModel):
    """다이제스트 내 스크랩 항목."""

    id: str
    title: str
    type: str
    summary: str | None = None
    tags: list[str] = []
    created_at: str


class DigestDiaryItem(BaseModel):
    """다이제스트 내 다이어리 항목."""

    id: str
    mood: str
    preview: str
    created_at: str


class DigestSummary(BaseModel):
    """하루 활동 집계."""

    scrap_count: int
    diary_count: int
    chat_count: int


class DigestInsights(BaseModel):
    """AI 생성 인사이트."""

    main_topics: list[str]
    suggested_questions: list[str]


class DigestResponse(BaseModel):
    """일일 다이제스트 전체 응답."""

    date: str
    summary: DigestSummary
    scraps: list[DigestScrapItem]
    diaries: list[DigestDiaryItem]
    chats: list[dict]
    insights: DigestInsights
