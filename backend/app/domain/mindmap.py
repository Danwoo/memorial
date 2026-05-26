"""마인드맵 도메인 모델 (Pydantic).

KuzuDB raw 결과(dict)와 D3 시각화 결과(dict) 사이에서 비즈니스적으로 의미 있는
형태만 도메인 엔티티로 모델링한다.

마이그레이션 정책:
- save_entities/save_relations 입력은 list[dict] 유지 — LLM 도구 출력과 직접 연결
- get_graph_data 결과는 dict 유지 — D3 호환 와이어 포맷
- find_shortest_path 결과는 MindmapShortestPath 도메인 모델 (reasoning trace)
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class MindmapEntity(BaseModel):
    """그래프 노드 — Knowledge Graph의 엔티티."""

    model_config = ConfigDict(frozen=True)

    name: str
    type: str = "Concept"


class MindmapRelation(BaseModel):
    """그래프 엣지 — Knowledge Graph의 관계."""

    model_config = ConfigDict(frozen=True)

    source: str
    target: str
    rel_type: str = "RELATED_TO"


class MindmapShortestPath(BaseModel):
    """두 엔티티 사이 최단 경로 — Analyst의 reasoning trace 결과."""

    model_config = ConfigDict(frozen=True)

    names: list[str]      # 경로상 엔티티 시퀀스 (시작 → 끝)
    rel_types: list[str]  # 간선 타입 시퀀스 (names보다 1개 짧음)
    hops: int             # 경로 길이 (=len(rel_types))

    @property
    def explanation(self) -> str:
        """사람이 읽기 좋은 reasoning trace 문자열."""
        if not self.rel_types:
            return " → ".join(self.names)
        segments = [
            f"{self.names[i]} →({rel})→ {self.names[i + 1]}"
            for i, rel in enumerate(self.rel_types)
            if i + 1 < len(self.names)
        ]
        return " ".join(segments)
