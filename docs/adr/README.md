# Architecture Decision Records

여기 모인 ADR은 백엔드 아키텍처의 **굵직한 결정**의 컨텍스트·트레이드오프·대안을 기록한다.
새 결정을 내리거나 기존 결정을 뒤집을 때는 새 ADR을 추가한다 (기존 ADR은 supersede 표시).

## Status 정의

- **Accepted**: 현재 적용 중인 결정
- **Superseded by ADR-NNN**: 다른 ADR로 대체됨
- **Deprecated**: 더 이상 권장되지 않으나 코드에 남아있음

## 목록

| # | 제목 | Status |
|---|---|---|
| [001](001-graph-db-choice.md) | KuzuDB를 Knowledge Graph 저장소로 선택 | Accepted |
| [002](002-repository-protocol.md) | Repository Protocol을 통한 의존성 역전 | Accepted |
| [003](003-orchestrator-pattern.md) | Cross-domain 흐름은 Orchestrator로만 | Accepted |
| [004](004-three-layer-models.md) | DB row · 도메인 엔티티 · API DTO 3계층 분리 | Accepted |
| [005](005-llm-provider-strategy.md) | OpenRouter primary + Gemini fallback | Accepted |
| [006](006-graph-multi-tenancy.md) | Memory 노드 user-namespacing 보류 | Accepted |
| [007](007-agent-container-lifetime.md) | AgentContainer 인스턴스 수명 정책 | Accepted |
| [008](008-entity-canonicalization.md) | 엔티티 canonicalization 정적 dict → 동적 로드맵 | Accepted |
