from typing import Any

from pydantic import BaseModel


class GraphNode(BaseModel):
    """지식 그래프 노드."""

    id: str
    label: str
    name: str = ""
    group: str = ""
    val: int = 1
    properties: dict[str, Any] = {}


class GraphLink(BaseModel):
    """지식 그래프 엣지."""

    source: str
    target: str
    type: str
    properties: dict[str, Any] = {}


class GraphDataResponse(BaseModel):
    """그래프 시각화 데이터 응답."""

    nodes: list[GraphNode]
    links: list[GraphLink]


class EntityInput(BaseModel):
    """그래프에 저장할 엔티티 입력."""

    name: str
    type: str


class RelationInput(BaseModel):
    """그래프에 저장할 관계 입력."""

    source: str
    target: str
    type: str
