from typing import Any

from pydantic import BaseModel


class MindmapNode(BaseModel):
    """마인드맵 노드."""

    id: str
    label: str
    name: str = ""
    group: str = ""
    val: int = 1
    properties: dict[str, Any] = {}


class MindmapLink(BaseModel):
    """마인드맵 엣지."""

    source: str
    target: str
    type: str
    properties: dict[str, Any] = {}


class MindmapDataResponse(BaseModel):
    """마인드맵 시각화 데이터 응답."""

    nodes: list[MindmapNode]
    links: list[MindmapLink]


class EntityInput(BaseModel):
    """마인드맵에 저장할 엔티티 입력."""

    name: str
    type: str


class RelationInput(BaseModel):
    """마인드맵에 저장할 관계 입력."""

    source: str
    target: str
    type: str
