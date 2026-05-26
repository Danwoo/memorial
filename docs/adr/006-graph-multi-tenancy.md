# ADR-006: Memory 노드 user-namespacing 보류, Entity는 글로벌

**Status**: Accepted
**Date**: 2026-02

## 컨텍스트

KuzuDB 스키마 결정 시점에 가장 큰 질문: **multi-tenancy를 어떻게?**

선택지:
- (A) Entity 노드를 user별로 분리 (`Entity_user1`, `Entity_user2`)
- (B) Entity는 글로벌 + `Memory` 노드만 user_id 보유, `MENTIONS` 관계로 격리 — **선택**
- (C) 별도 KuzuDB instance per user

## 결정

**(B) Entity 글로벌 + Memory가 user_id 보유**:

```cypher
CREATE NODE TABLE Entity(name STRING, type STRING, PRIMARY KEY(name))
CREATE NODE TABLE Memory(id STRING, user_id STRING, PRIMARY KEY(id))
CREATE REL TABLE MENTIONS(FROM Memory TO Entity)
CREATE REL TABLE ENTITY_REL(FROM Entity TO Entity, rel_type STRING)
```

쿼리에서 user 격리는 Memory를 거치는 경로로:
```cypher
MATCH (mem:Memory {user_id: $user_id})-[:MENTIONS]->(e:Entity)
```

## 근거

### Entity 글로벌의 이점

- **자동 dedup**: 사용자 A가 "React"를 저장하고 B도 "React"를 저장하면 같은 노드.
  Entity 폭발(node explosion) 방지.
- **canonicalization 자연스러움**: "리액트"/"ReactJS" → "React"로 합쳐지면 자동으로 글로벌 머지.
- **잠재적 공유 인사이트**: 향후 "이 주제 다른 사용자도 관심 있음" 같은 기능 가능.

### user 격리의 안전성

- `MENTIONS` 관계가 user-scoped이므로 사용자 A가 만든 Entity가 B의 Entity 검색에 잡혀도
  관계는 보이지 않음 (`MATCH ... WHERE EXISTS { ... user_id = $user }`).
- Repository 모든 쿼리가 user_id 필수.

## 트레이드오프 / 알려진 한계

### 1. ENTITY_REL이 user 격리 안 됨

- 사용자 A가 만든 `(React)-[USES]->(JSX)` 관계가 B의 그래프 시각화에도 보일 수 있음.
- **대응**: 이미 코드에 user 격리 적용. `mindmap/_visualization.py`의 `_query_entity_relations`
  가 양쪽 끝점 모두 `user_id` Memory의 mention 경로로 제한:
  ```cypher
  MATCH (mem:Memory {user_id})-[:MENTIONS]->(n:Entity)-[r:ENTITY_REL]->(m:Entity)
        <-[:MENTIONS]-(mem2:Memory {user_id})
  ```
  → 양쪽 endpoint가 같은 user의 Memory에 mention된 ENTITY_REL만 보임.

### 2. Entity 노드는 user_id가 없어 단독 인덱스 불가

- "user A가 다룬 Entity 목록"은 항상 Memory join 필요 — 인덱스 추가 못 함.
- **대응**: KuzuDB 0.11에서 secondary index 미지원 ([ADR-001 참고]). FTS로
  엔티티 이름 검색은 가속됨. 운영 데이터 노드 100,000+ 가면 옵션 (A) 재검토.

### 3. 글로벌 Entity가 다른 user의 데이터를 reveal하나?

- 직접 노드는 보이지 않음 (`MENTIONS` 경로로만 user 데이터 노출).
- **다만** `Entity.name` 자체가 PII가 될 수 있음 (예: 개인 이름). LLM이 추출하지 않도록
  prompt rule 적용 (`_EXTRACT_ENTITIES_SYSTEM` few-shot에서 감정 일기는 entity 0 반환).

## 부팅 시 KuzuDB rebuild 정책

- ephemeral 디스크 환경에서는 부팅 시 Supabase의 `extracted_entities/relations` 컬럼으로
  rebuild (`MindmapService.rebuild_from_supabase`).
- 영구 디스크 환경에서는 `count_memory_nodes() > 0`이면 skip — idempotent.

## 재평가 트리거

- PII 노출 사고 발생 (Entity name 자체가 sensitive)
- 사용자별 graph 통계가 핫 패스가 됨 (Memory join 비용 부담)
