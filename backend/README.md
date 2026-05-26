# Memoir AI — Backend

Python FastAPI 기반 백엔드. Knowledge Graph(KuzuDB) + 벡터 검색(Supabase pgvector) +
멀티 에이전트(LangGraph) 기반 회고/지식 시스템.

## Setup
```bash
poetry install
poetry run uvicorn app.main:app --reload
```

테스트:
```bash
poetry run pytest tests/ --ignore=tests/test_curator_url.py --ignore=tests/scenario_test.py
```

## 디렉토리 구조

```
app/
├── config/                       # 환경 설정, DI factory, auth, 미들웨어
│   ├── settings.py               # pydantic-settings 기반 환경변수
│   ├── dependencies.py           # FastAPI Depends 팩토리 (Repo/Service 조립)
│   ├── auth.py                   # Supabase JWT 검증 + 사용자 컨텍스트
│   ├── middleware.py             # RequestContextMiddleware + RateLimit
│   └── llm.py                    # LLM 팩토리 (OpenRouter ↔ Gemini fallback)
│
├── domain/                       # Pydantic 도메인 엔티티 (DB row, API DTO와 분리)
│   ├── chat.py                   # ChatSession, ChatMessageRecord, ChatSessionSummary
│   ├── diary.py                  # DiaryEntry
│   └── mindmap.py                # MindmapEntity, MindmapRelation, MindmapShortestPath
│
├── repositories/                 # 영속화 계층
│   ├── protocols/                # 의존성 역전용 Protocol 정의
│   │   ├── chat_repository_protocol.py
│   │   ├── diary_repository_protocol.py
│   │   ├── scrap_repository_protocol.py
│   │   ├── mindmap_repository_protocol.py
│   │   ├── calendar_repository_protocol.py
│   │   └── vector_repository_protocol.py
│   ├── mindmap/                  # KuzuDB Repository (mixin 분할)
│   │   ├── _base.py              # 초기화, schema, FTS 인덱스, 공통 헬퍼
│   │   ├── _storage.py           # save_entities/relations (UNWIND 배치)
│   │   ├── _query.py             # ego graph, hub, orphan, search 등
│   │   ├── _path.py              # find_shortest_path (reasoning trace)
│   │   ├── _visualization.py     # D3 호환 그래프 데이터
│   │   ├── _maintenance.py       # delete_memory_node
│   │   ├── _aliases.py           # 엔티티 canonicalization 동의어 사전
│   │   ├── _constants.py         # 라벨 화이트리스트, 매직 넘버
│   │   └── _repository.py        # MindmapRepository(mixin 조합)
│   ├── chat_repository.py        # 채팅 세션/메시지/피드백
│   ├── diary_repository.py       # 다이어리 + 감정 분석
│   ├── scrap_repository.py       # 콘텐츠 스크랩
│   ├── calendar_repository.py    # 활동 집계
│   ├── vector_repository.py      # 임베딩 저장/유사도 검색
│   └── notification_repository.py
│
├── orchestrators/                # Cross-domain 흐름 (도메인 경계 명시)
│   └── diary_orchestrator.py     # 다이어리 → 스크랩 적재 → Librarian 엔티티 추출
│
├── services/                     # 비즈니스 로직 (모든 Repository는 Protocol로 의존)
│   ├── chat_service.py
│   ├── diary_service.py / diary_analysis_service.py
│   ├── scrap_service.py
│   ├── mindmap_service.py / mindmap_insight_service.py
│   ├── search_service.py / hybrid_search_service.py
│   ├── graphrag_indexing_service.py / graphrag_retrieval_service.py
│   ├── digest_service.py / nudge_service.py / report_service.py / insight_service.py
│   ├── duplicate_service.py / export_service.py
│   ├── community_summary_service.py
│   ├── kakao_channel_service.py
│   ├── scheduler_service.py      # APScheduler 작업
│   └── ingest_service.py         # URL fetch + SSRF 방어 + PDF parse
│
├── agents/                       # LangGraph 멀티 에이전트
│   ├── streaming/                # 그래프별 스트리밍 전략 (ReAct / DAG)
│   ├── registry.py               # AgentRegistry + capability 모델
│   ├── container.py              # 노드용 DI 컨테이너 (FastAPI DI 외부)
│   ├── base_context.py           # AgentContext (Protocol 의존)
│   ├── socrates/ oracle/ librarian/ analyst/ scribe/ curator/ reporter/ supervisor/
│   ├── shared/                   # 공통 노드/유틸 (enrichment_utils 등)
│   └── tools/                    # 7개 도구 카테고리 (graph/diary/retrieval/...)
│
├── observability/                # 관찰성
│   ├── context.py                # contextvars (request_id, user_id) + Filter
│   ├── llm_callback.py           # 토큰 사용량 자동 로깅
│   └── logging_config.py         # dictConfig — uvicorn 로거 포함 일관 포맷
│
├── routers/                      # FastAPI 라우터 (얇은 layer — Service 위임만)
│   ├── chat_router.py            # /api/v1/socrates/*
│   ├── diary_router.py / scrap_router.py / mindmap_router.py
│   ├── search_router.py / digest_router.py / report_router.py / ...
│   └── router.py                 # api_router 조립
│
├── schemas/                      # API DTO (요청/응답)
├── exceptions.py                 # 도메인 예외 계층 (LLMError, IngestError, ...)
├── utils/                        # parse_iso_datetime, cache, llm parser
└── main.py                       # FastAPI 앱 + lifespan
```

## 설계 원칙

- **3계층 분리**: DB row → Pydantic 도메인 엔티티 → API DTO
  Repository는 도메인 모델 반환, Router에서 DTO로 매핑.
- **의존성 역전**: 모든 Service는 `RepositoryProtocol`에만 의존.
  구현체 교체/테스트 fake 주입이 자유롭다.
- **Cross-domain 경계**: 다른 prefix를 호출하는 흐름은 `Orchestrator`로만.
- **에이전트 capability 모델**: AgentRegistry는 (graph, streaming strategy)
  쌍으로 등록되어 ReAct/DAG 양쪽을 같은 인터페이스로 노출.
- **그래프 reasoning**: 단순 neighborhood 외에 `find_shortest_path`로
  reasoning trace 제공 (Analyst tool로 노출).
- **LLM 품질**: Pydantic `with_structured_output` + 한국어 few-shot prompt +
  토큰 사용량 자동 로깅 (모든 LLM 호출).
- **관찰성**: `X-Request-ID` 헤더 echo + contextvars로 모든 로그에
  `[rid=... user=...]` 자동 부착.

## 테스트 정책

- `tests/test_*` — 단위/도메인 모델 테스트
- `tests/integration/` — TestClient + dependency_overrides로 라우터 contract 검증
- 외부 HTTP를 호출하는 시나리오는 별도 (실행 시 제외)
