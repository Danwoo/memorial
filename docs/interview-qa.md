# 면접 예상 질문 & 답변 가이드

각 답변은 **(코드 위치 / ADR / 벤치마크)** 셋 중 하나로 근거를 제시한다.
"왜 이렇게 했어?" 질문에 막연한 답이 아니라 측정/문서/구체 코드로 답할 수 있도록.

---

## 아키텍처 결정

### Q1. "왜 KuzuDB를 골랐어요? Neo4j 안 쓰고."

**답변 포인트**
- 운영 환경 제약: EC2 t2.micro (1GB RAM). Neo4j는 별도 JVM — 비현실적.
- KuzuDB는 임베디드. `buffer_pool_size=32MB`로 명시 제한 (`mindmap/_base.py:34`).
- Cypher 호환 → Neo4j 경험 그대로.
- 트레이드오프 인지: secondary index 미지원, 운영 사례 적음 → ADR-001에 명시.

**근거**: [ADR-001](adr/001-graph-db-choice.md)

---

### Q2. "Repository Protocol 왜 도입? 그냥 duck typing 두면 안 돼?"

**답변 포인트**
- 의존성 역전 원칙: Service는 인터페이스에 의존. 구현체 교체/테스트 fake 주입 자유.
- mypy/IDE에서 시그니처 drift 감지 가능.
- 6개 도메인 모두 적용 (Chat/Diary/Scrap/Mindmap/Calendar/Vector).
- 트레이드오프: DI factory(`config/dependencies.py`)는 여전히 구체 알아도 됨 — composition root 패턴.

**근거**: [ADR-002](adr/002-repository-protocol.md), `app/repositories/protocols/` 폴더

---

### Q3. "Orchestrator 패턴은 왜? Service에 직접 cross-domain 메서드 추가하면 안 돼?"

**답변 포인트**
- DiaryService가 ScrapService에 의존하면 양방향 결합 위험.
- Cross-domain 흐름의 위치를 한곳에 명시 — `app/orchestrators/diary_orchestrator.py`.
- 같은 prefix끼리는 직접 의존 가능, cross-domain은 반드시 orchestrator 경유.
- Saga 패턴 안 쓴 이유: graceful degradation으로 충분, 결제처럼 강한 일관성 요구 안 함.

**근거**: [ADR-003](adr/003-orchestrator-pattern.md)

---

### Q4. "왜 도메인 모델, DTO, DB row 3개를 따로?"

**답변 포인트**
- 각 계층의 변경 이유가 다름:
  - DB row: 인프라(Supabase/Kuzu) 변경 시
  - 도메인 엔티티: 비즈니스 불변식 변경 시
  - DTO: 외부 계약(frontend) 변경 시
- 변환 비용 < 1ms 측정, 명확함이 비용 압도.
- 분석성 메서드(통계/내보내기)는 형태 가변적이라 dict 유지 — 일관성보다 실용성.

**근거**: [ADR-004](adr/004-three-layer-models.md)

---

## 그래프 / KuzuDB 디테일

### Q5. "UNWIND가 빠르다고 commit에 적었는데 측정했어요?"

**답변 포인트**: 했다.

```
[scripts/bench/bench_graph_batch.py 결과]
엔티티     for-loop      UNWIND        speedup
10        71ms          21ms          3.3x
50        278ms         16ms          17.6x
200       1195ms        20ms          60.7x
1000      5459ms        34ms          159.4x
```

엔티티 수가 늘수록 차이 폭발 — 원인은 plan compile N회 vs 1회.

**근거**: `scripts/bench/bench_graph_batch.py`

---

### Q6. "Shortest path 어떻게 구현했어요? 그냥 BFS인가요?"

**답변 포인트**
- KuzuDB native `* SHORTEST 1..N` 키워드 사용 (`mindmap/_path.py:36`).
- 발견 과정 솔직히 공유: **초기 구현은 Neo4j 표준 `[n IN nodes(p) | n.name]` 리스트
  컴프리헨션을 썼는데 KuzuDB 0.11에선 binder 에러 — `list_transform(nodes(p), x -> x.name)`이 정답**.
  벤치마크 만들면서 발견했고 즉시 정정 + 통합 테스트 추가.
- 사용자 KB 소유권 검증을 path query 안에 통합 (Memory를 거쳐 mention 경로로).
- 결과는 `MindmapShortestPath` 도메인 모델 (`names`, `rel_types`, `hops`, `.explanation` property).

**근거**: `app/repositories/mindmap/_path.py`, `tests/test_shortest_path.py` (6 tests 통합 검증),
`scripts/bench/bench_shortest_path.py`

---

### Q7. "엔티티 canonicalization을 정적 dict로 했는데 sustainable한가요?"

**답변 포인트**: 솔직히 1단계만 충분. 운영 데이터 모이면 2단계 자동화로 이전.

- 1단계 (현재): 정적 dict 50개 — JS/Python/AI/ML/DB 도메인 주요 동의어 커버.
- 2단계 (트리거: 노드 1000+): embedding 유사도 + 동시 등장 빈도로 후보 자동 발견.
  스켈레톤 이미 작성 (`mindmap/_alias_discovery.py`) — 운영자 검토 후 dict에 동적 추가.
- 3단계 (트리거: 노드 10000+): 실시간 lookup, UI에서 사용자 confirm.
- 처음부터 embedding 안 쓴 이유: false positive 위험 + 임계값 튜닝에 운영 데이터 필요.

**근거**: [ADR-008](adr/008-entity-canonicalization.md), `tests/test_canonicalize.py` (8 tests)

---

### Q8. "Memory 노드만 user_id 있고 Entity는 글로벌이네요. 데이터 격리 안전한가요?"

**답변 포인트**
- 사용자 격리는 `MENTIONS` 관계로 — 모든 쿼리가 `MATCH (mem:Memory {user_id})-[:MENTIONS]->(e)` 경유.
- ENTITY_REL 시각화도 양 끝점 모두 user의 Memory mention 검증 (`_visualization.py`).
- Entity 글로벌의 이점: dedup 자동, canonicalization 자연스러움.
- 단점: Entity 이름 자체가 PII 될 수 있음 — LLM prompt rule (`_EXTRACT_ENTITIES_SYSTEM`)이
  감정 일기에서 entity 0 반환하도록 few-shot으로 학습.

**근거**: [ADR-006](adr/006-graph-multi-tenancy.md)

---

## LLM 디테일

### Q9. "왜 OpenRouter? 운영 신뢰성은요?"

**답변 포인트**: 프로토타입 단계의 명시적 선택. 운영 진입 시 즉시 전환 가능.

- `_USE_OPENROUTER = False` 한 줄 변경으로 OpenAI 유료 모델 전환.
- LangChain `with_fallbacks([Gemini])`로 OpenRouter 장애 시 자동 Gemini.
- `TokenUsageLogger` callback이 모든 호출 token 자동 로깅 (label로 추적).
- 재평가 트리거: 일 1000 호출 초과 / SLA 약속 필요 시.

**근거**: [ADR-005](adr/005-llm-provider-strategy.md), `app/config/llm.py`, `app/observability/llm_callback.py`

---

### Q10. "LLM 응답 파싱 어떻게 안전하게? JSON 깨지면?"

**답변 포인트**: Pydantic `with_structured_output` 강제.

- `graph_schemas.py`에 `EntityExtractionResult`, `RelationExtractionResult` 등 정의.
- `llm.with_structured_output(Schema)` — provider가 native tool calling/JSON mode로 강제.
- Few-shot examples로 정확도 보강 (`_EXTRACT_ENTITIES_SYSTEM` 4개, `_CBT_PROMPT` 5개 등).
- 실패 시 graceful: 빈 리스트 반환 + `logger.exception` (silent crash 안 함).

**근거**: `app/agents/tools/graph_schemas.py`, `graph_tools.py`

---

## 테스트 / 운영

### Q11. "테스트 116개 있는데 실제 DB 통합은요? 다 mock 아닌가?"

**답변 포인트**: 솔직히 일부 그렇다. 다만 핵심 GraphDB는 진짜 KuzuDB.

- `tests/test_shortest_path.py`: 임시 KuzuDB로 6개 테스트 — 실제 cypher 실행.
- `tests/integration/`: TestClient + dependency_overrides로 router contract 검증 (service mock).
- Supabase는 mock — 외부 클라우드 의존 회피.
- 운영 검증을 위해 향후 testcontainer + Supabase local emulator 검토.

**근거**: `tests/test_shortest_path.py`, `tests/integration/`

---

### Q12. "에러 경로 테스트는요? 행복 경로만 있는 거 아닌가요?"

**답변 포인트**: 14개 에러 경로 테스트 있다.

- `tests/test_error_paths.py`:
  - **SSRF**: localhost, 127.0.0.1, 10.0.0.0/8, AWS metadata 169.254.169.254 차단
  - **URL 스킴**: ftp/file/javascript 거부
  - **LLM 실패**: LLMError → 친절 메시지 + 내부 메시지 누설 안 함
  - **알려지지 않은 예외**: 일반화 메시지, stack trace 미노출
  - **CancelledError**: SSE 연결 해제 graceful (에러 메시지 X)

**근거**: `tests/test_error_paths.py` (14 tests)

---

### Q13. "AgentContainer가 매 호출마다 생성되는데 성능은요?"

**답변 포인트**: 측정했다. median 0.124ms.

```
[scripts/bench/bench_container.py 1000회]
median: 0.124ms / p95: 0.203ms / p99: 0.313ms
```

RAG 응답 시간(수백 ms~수 초)의 0.05% 미만 — `lru_cache` singleton보다 stateless가 명확.
MindmapRepository만 예외 — `@lru_cache` singleton (KuzuDB Database 초기화 비용).

**근거**: [ADR-007](adr/007-agent-container-lifetime.md), `scripts/bench/bench_container.py`

---

### Q14. "request_id 추적은 어떻게? distributed tracing 가능?"

**답변 포인트**
- `X-Request-ID` 헤더 echo + 없으면 새로 생성 (12자 hex, 64자 초과 거부 — injection 방어).
- `contextvars`로 비동기 안전 request-scope.
- `RequestContextFilter`가 모든 LogRecord에 자동 부착 — `[rid=abc123 user=xxx] message`.
- uvicorn access log까지 같은 포맷.
- 다음 단계: OpenTelemetry adapter로 LangSmith/Jaeger 연동 (callback handler 1개 추가).

**근거**: `app/observability/context.py`, `logging_config.py`, `middleware.py:RequestContextMiddleware`,
`tests/integration/test_health_api.py` (4 tests)

---

## 약점에 대한 솔직한 답변

### Q15. "이 코드의 가장 큰 약점이 뭐예요?"

**답변** (솔직히):
1. **운영 데이터 0** — 모든 성능 주장이 합성 벤치마크. 실 사용자 트래픽 없어 부하 패턴 모름.
2. **E2E 통합 테스트 일부 mock** — `tests/integration/`이 service mock 기반. KuzuDB는 진짜 통합이지만 Supabase 측은 mock. testcontainer 미도입.
3. **canonicalize 50개 시드** — 새 도메인 진입 시 즉시 한계. 자동화 코드는 스켈레톤 작성됐지만 활성화 안 함.
4. **mypy 미적용** — Protocol drift는 ruff로 못 잡음. CI에 mypy strict 추가 검토.
5. **OpenRouter 무료 티어** — SLA 없음. 프로토타입에서는 합리적이나 운영 시 즉시 전환 필요.

이 약점들은 ADR에 다 명시되어 있고, 트리거 조건 + 마이그레이션 경로도 문서화.

---

### Q16. "이 프로젝트 다시 한다면 뭘 다르게 할 거예요?"

**답변**
1. **mypy strict from day-1** — Protocol drift 자동 감지.
2. **벤치마크 from day-1** — 성능 가정 검증.
3. **운영 telemetry 우선** — request_id, token usage, slow query log를 처음부터.
4. **canonicalize를 처음부터 동적 자동 추출 + 수동 검토 hybrid** — 정적 dict 폐기.
5. **거대 파일이 800줄 되기 전에 분할** — `mindmap_repository.py`가 그 단계 직전에야 패키지화.
