from pydantic import BaseModel


class DailyInsight(BaseModel):
    """일일 인사이트 항목."""

    type: str  # "pattern" | "connection" | "action"
    icon: str
    title: str
    description: str
    cta_label: str
    cta_path: str


class DailyInsightsResponse(BaseModel):
    """일일 인사이트 응답."""

    insights: list[DailyInsight] = []
