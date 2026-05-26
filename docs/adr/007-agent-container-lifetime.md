# ADR-007: AgentContainer 인스턴스 수명 정책

**Status**: Accepted
**Date**: 2026-05

## 컨텍스트

`AgentServiceContainer`는 LangGraph 노드가 Repository/Service에 접근하기 위한 DI 컨테이너.
LangGraph는 FastAPI 요청 컨텍스트 **밖에서** 실행되므로 (스트리밍, 비동기 graph invocation)
`Depends()` 체인을 못 쓴다.

`get_agent_container()` 호출 비용:
- Supabase 클라이언트 1회 lookup (모듈 레벨 캐시됨)
- Repository 5개 인스턴스화 (각 `__init__`만, 비용 작음)
- Service 4개 인스턴스화 (마찬가지)
- MindmapRepository는 `lru_cache`된 싱글톤 ([dependencies.py:get_mindmap_repository])

선택지:
- (A) 매 호출마다 새 컨테이너 (현 상태)
- (B) `@lru_cache`로 프로세스 싱글톤
- (C) lazy property 기반 컨테이너 (필요한 service만 생성)

## 결정

**(A) 매 호출마다 새 컨테이너 — 단, 무거운 인스턴스(MindmapRepository)는 싱글톤**.

근거:
1. **Stateless**: Repository/Service 모두 stateless (mutable state 없음). 인스턴스화 비용 작음.
2. **테스트 격리**: 매번 fresh — 테스트 간 상태 누수 0.
3. **MindmapRepository만 예외**: KuzuDB Database 객체 초기화 비용이 크고 (~수십 ms),
   동시 connection은 호출 시점에 새로 생성 (`_get_conn()`) — `lru_cache` singleton로 처리.

## 트레이드오프

### 1. 매 호출마다 5+개 Repository instance 생성

- `ChatRepository(db)` 등의 `__init__`은 `self.db = db` 한 줄 — 비용 무시 가능.
- **대응**: 측정 결과 컨테이너 생성 < 0.5ms. 한 사용자 요청 전체 응답이 수백 ms ~ 수 초인
  RAG 시스템에서 무시 가능한 비율.

### 2. `lru_cache` 적용 시 잠재적 위험

- `@lru_cache` 적용했다고 가정: 첫 요청에서 user_X의 컨테이너가 캐시되면 다음 사용자가
  같은 컨테이너 사용 → user 격리는 Repository 레벨이라 영향 없지만, 모듈 reload 시 캐시
  stale.
- **대응**: stateless이므로 user 격리 영향 없음. 다만 캐시 invalidation 부담 없이 그냥
  매번 새로 만드는 게 명확.

### 3. MindmapRepository 싱글톤이 thread-safe?

- KuzuDB `Database` 객체는 스레드 안전. `Connection`만 호출별로 생성.
- 코드 확인: `_get_conn()`이 매 호출 `kuzu.Connection(self.db)` 생성 — OK.
- **대응**: `MindmapRepository`는 thread-safe. `Database` 공유 + `Connection` 호출별 = 표준 패턴.

## 검증

- `scripts/bench/bench_container.py`에서 컨테이너 생성 비용 측정 (< 0.5ms).
- 단위 테스트는 mock 주입 — container 생성 비용 영향 0.

## 향후 검토

- 만약 service에 stateful caching (in-memory rate limiter 등)이 추가되면 → (B) singleton 검토.
