"""그래프 도구용 Pydantic structured output schema.

LLM에 `with_structured_output(Schema)`로 바인딩되어:
- 응답 형식을 강제 (parse 실패 가능성 감소)
- type 안정성 확보
- LLM이 schema description으로 추가 가이드 수신

LangChain이 provider별 native structured output (OpenAI tool calling,
Anthropic structured) 또는 JSON mode로 fallback해 처리한다.
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class ExtractedEntity(BaseModel):
    """추출된 엔티티 — 그래프 노드 후보."""

    name: str = Field(..., description="엔티티의 정식 명칭 (가능하면 영문 canonical name)")
    type: str = Field(
        ...,
        description=(
            "엔티티 타입 — 다음 중 하나: "
            "Concept, Person, Organization, Location, Event, Technology, Product, "
            "Topic, Idea, Company, Platform, Framework, Language, Tool, Project"
        ),
    )


class EntityExtractionResult(BaseModel):
    """엔티티 추출 결과."""

    entities: list[ExtractedEntity] = Field(default_factory=list, max_length=15)


class ExtractedRelation(BaseModel):
    """추출된 관계 — 그래프 엣지."""

    source: str = Field(..., description="출발 엔티티 이름 (입력 엔티티 목록에 존재해야 함)")
    target: str = Field(..., description="도착 엔티티 이름 (입력 엔티티 목록에 존재해야 함)")
    rel_type: str = Field(
        ...,
        description=(
            "관계 타입 — 가능한 가장 구체적인 것을 선택. "
            "RELATED_TO는 다른 타입이 모두 부적합할 때만 사용."
        ),
    )


class RelationExtractionResult(BaseModel):
    """관계 추출 결과."""

    relations: list[ExtractedRelation] = Field(default_factory=list, max_length=15)


class SuggestedConnection(BaseModel):
    """추천된 잠재적 연결."""

    source: str = Field(..., description="출발 엔티티 이름")
    target: str = Field(..., description="도착 엔티티 이름")
    rel_type: str = Field(..., description="제안된 관계 타입")
    reason: str = Field(..., description="이 연결이 왜 의미 있는지에 대한 한국어 설명")


class ConnectionSuggestionResult(BaseModel):
    """연결 추천 결과."""

    suggestions: list[SuggestedConnection] = Field(default_factory=list, max_length=10)
