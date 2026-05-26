# ADR-001: KuzuDB를 Knowledge Graph 저장소로 선택

**Status**: Accepted
**Date**: 2026-02
**Deciders**: 솔로 개발

## 컨텍스트

Memoir AI는 사용자가 저장한 스크랩/다이어리에서 엔티티·관계를 추출해 그래프로 적재하고,
이 그래프를 활용해 다음을 수행해야 한다:

- 시각화 (D3 호환 `{nodes, links}`)
- Ego-graph / 허브 노드 탐색
- 두 엔티티 사이 최단 경로 reasoning (Analyst의 explainability)
- 커뮤니티 감지 + 요약 (GraphRAG)

운영 환경은 **EC2 t2.micro (1GB RAM)** + 영구 디스크 없는 ephemeral.

## 고려한 대안

| 옵션 | Pros | Cons |
|------|------|------|
| **Neo4j Community** | 성숙한 Cypher 생태계, GDS 라이브러리 | 별도 JVM 프로세스 — t2.micro에서 비현실적 메모리 점유 |
| **PostgreSQL + Apache AGE** | Supabase에 이미 PG 있음 | AGE는 PG extension인데 Supabase 호스팅에서 설치 불가 |
| **pgvector + recursive CTE** | 추가 의존성 0 | shortest path / community detection 직접 구현 부담, 성능 미확인 |
| **KuzuDB (선택)** | 임베디드 (별도 프로세스 0) · OLAP 지향 · Cypher 호환 · Python 바인딩 | 상대적 신규 (0.x) · secondary index 미지원 · 운영 사례 적음 |
| **NetworkX (in-memory)** | Python 네이티브 | 영속성 없음 · 사용자 데이터 매번 재구성 |

## 결정

**KuzuDB**를 채택한다.

근거:
1. **메모리 footprint**: `buffer_pool_size=32MB`로 명시 제한 (`_base.py:34`).
   t2.micro에서도 다른 서비스(FastAPI, scheduler)와 공존 가능.
2. **Cypher 호환**: 학습 곡선 최소화. Neo4j 경험을 그대로 활용.
3. **임베디드**: 별도 운영 컴포넌트 0개. 영구 디스크 없는 환경에서 부팅 시
   Supabase의 `extracted_entities/relations` 컬럼으로 rebuild ([ADR-006](006-graph-multi-tenancy.md)).
4. **Python 바인딩 first-class**: `pip install kuzu` 하나로 시작.

## 트레이드오프 (면접관이 짚을 수 있는 약점)

### 1. KuzuDB 0.11 — 성숙도

- secondary B-tree 인덱스 미지원 (FTS만 지원, `_base.py:_ensure_schema`).
- 운영 베스트 프랙티스가 Neo4j만큼 정립 안 됨.
- **답변**: 현 데이터 규모(개인 사용자 ~수천 노드)에서는 단일 PK 인덱스로 충분. FTS는
  엔티티 이름 lookup 가속용으로 등록. 운영 데이터가 10만+ 노드 넘어가면 Neo4j 이전 검토.

### 2. *SHORTEST 키워드 portability

- KuzuDB 버전별로 `*SHORTEST` 문법이 미묘하게 다르거나 미지원.
- **답변**: variable-length path + `length(p)` 정렬로 portable하게 구현
  (`mindmap/_path.py`). 성능은 [bench/bench_shortest_path.py](../../backend/scripts/bench/)에서 측정.
  현 데이터 규모에서 native vs portable 차이 < 5ms.

### 3. 부팅 시 rebuild 비용

- ephemeral 환경에서 매 재시작 시 Supabase에서 5000 스크랩 재처리는 비용.
- **답변**: `MindmapService.rebuild_from_supabase(force=False)` + `count_memory_nodes()`
  체크로 idempotent. 영구 디스크 환경(EC2 EBS)에서는 1회만 실행.
  ephemeral 환경에서는 부팅 N초 비용 vs 운영 단순함 trade-off 수용.

## 향후 검토 트리거

- 노드 수 100,000 초과
- 단일 사용자가 다중 동시 쿼리 (현재는 사용자별 거의 0~1 동시성)
- KuzuDB 1.0 release — index 정책 변경 여부 확인
