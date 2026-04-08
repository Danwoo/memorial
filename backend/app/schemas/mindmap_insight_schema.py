from pydantic import BaseModel, Field


class ClusterInfo(BaseModel):
    """클러스터 정보."""

    cluster_id: int
    entities: list[str]
    entity_types: list[str]
    size: int
    summary: str = ""


class TrendItem(BaseModel):
    """태그 트렌드 항목."""

    tag: str
    counts: list[int]
    direction: str  # "up" | "down" | "stable"


class IsolatedNode(BaseModel):
    """고립 노드 (관계 없는 엔티티)."""

    name: str
    type: str


class HubNode(BaseModel):
    """허브 노드 (degree 상위)."""

    name: str
    type: str
    degree: int


class MindmapInsightsResponse(BaseModel):
    """마인드맵 인사이트 전체 응답."""

    clusters: list[ClusterInfo] = []
    trends: list[TrendItem] = []
    isolated_nodes: list[IsolatedNode] = []
    hub_nodes: list[HubNode] = []


class CreateRelationRequest(BaseModel):
    """수동 관계 생성 요청."""

    source: str = Field(max_length=500)
    target: str = Field(max_length=500)
    rel_type: str = Field("RELATED_TO", max_length=100)
