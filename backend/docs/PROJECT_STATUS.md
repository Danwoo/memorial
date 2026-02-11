# Memoir - 프로젝트 현재 상태

> 최종 업데이트: 2026-02-11
>
> **NOTE**: Neo4j는 KuzuDB(임베디드 그래프 DB)로 마이그레이션 완료.
> 아래 Neo4j 관련 내용은 역사적 기록으로 남겨둠.

## 서비스 개요

AI 기반 개인 지식 관리 + 성찰 시스템.
하루 동안 수집한 지식(웹 스크래핑, 카카오톡 메모, 노트)을 저녁에 AI와 대화하며 정리하고,
지식 그래프로 연결 관계를 발견하는 것이 핵심.

### 핵심 플로우

```
수집(WEB/NOTE/KakaoTalk) → Librarian(스크래핑→분류→요약→태깅→임베딩) → 저장
    ↓
Chat/Socrates(벡터+그래프 RAG) → 4개 모드(insight/counter/summary/evening)
    ↓
Journal(AI 초안 생성 → 사용자 편집 → 성찰 질문 → 인지왜곡 분석)
    ↓
Knowledge Graph(노드 클릭 → AI 대화 → 지식 확산)
```

### 기술 스택

| 영역 | 스택 |
|------|------|
| Backend | FastAPI + LangGraph + LangChain, Python 3.12, uv |
| Frontend | React 18 + Vite + TypeScript |
| DB | Supabase (PostgreSQL + pgvector), Neo4j AuraDB |
| AI | OpenAI GPT (text-embedding-3-small, GPT-4o) |
| 연동 | KakaoTalk (채널 봇 + 나에게 보내기), Upstage (PDF) |

---

## 기능 상태

### 동작 확인 완료

| 기능 | 상태 | 테스트 결과 |
|------|------|------------|
| Memory 목록/조회 | ✅ 정상 | 6건 저장, 5건 completed |
| Memory 생성 (WEB) | ✅ 정상 | Librarian 파이프라인 7초 내 처리 |
| Librarian Agent | ✅ 정상 | Curator→Ontologist→Save 순서 동작 |
| Chat/Socrates RAG | ✅ 정상 | 벡터 검색 → 컨텍스트 주입 → 응답 |
| SSE 스트리밍 | ⚠️ 시뮬레이션 | 전체 응답 후 50자 청크 분할 (실시간 아님) |
| Search (벡터 유사도) | ✅ 정상 | match_memories SQL 함수 버그 수정 완료 |
| Journal 저장/조회 | ✅ 정상 | |
| Journal 성찰 질문 | ✅ 정상 | AI가 질문 3개 생성 |
| Journal 인지왜곡 분석 | ✅ 정상 | distortions + wellness_score |
| Journal 관련 메모리 | ✅ 정상 | 벡터 검색으로 연결 |
| Digest (오늘) | ✅ 정상 | 오늘 데이터 + AI 추천 질문 |
| Stats/Activity/Timeline | ✅ 정상 | |
| Dashboard | ✅ 정상 | |
| Graph (Neo4j) | ✅ 정상 | Docker 로컬 Neo4j 실데이터 |
| PDF 업로드 | ✅ 정상 | Upstage Document Parse API 연동 |
| Journal AI 초안 | ✅ 정상 | evening 대화 기반 저널 초안 생성 |
| Digest date 필터 | ✅ 정상 | 날짜별 조회 동작 |
| 하이브리드 RAG | ✅ 정상 | 벡터 + Neo4j 그래프 traversal |
| Graph-Chat 연동 | ✅ 정상 | 노드 클릭 → ChatView 이동 |
| KakaoTalk OUT (보내기) | ✅ OAuth + API 구현 | 미연결 상태 (token 없음) |

### 미구현 / 이슈

| 우선순위 | 기능 | 상태 | 설명 | 관련 파일 |
|---------|------|------|------|-----------|
| P1 | KakaoTalk IN (채널 봇) | ❌ 미구현 | 카카오 비즈니스 채널 생성 → 웹훅 수신 → 메모리 저장. 외부 채널 설정 필요 | `services/kakao_service.py` |
| P2 | 그래프 Backfill | ✅ 완료 | POST /memories/backfill?force=true → 15개 메모리 → 61노드/60링크 | `routers/v1/memory_router.py` |
| P3 | Supabase Auth 키 확인 | ⚠️ 의심 | `sb_secret_` 형식 (정상은 `eyJ...`). 현재 DEBUG 모드로 우회 중 | `.env` |

---

## 수정 이력

### 2026-02-09 - 초기 점검 및 버그 수정

1. **Frontend .env 생성**: 파일 없어서 Supabase 클라이언트 null 반환 → `VITE_API_URL`, `VITE_SUPABASE_URL`, `VITE_SUPABASE_ANON_KEY` 추가
2. **Backend DEBUG=true**: `.env`에 추가하여 dev 인증 우회 활성화
3. **auth.py 수정**: 잘못된/만료된 토큰으로 요청 시에도 DEBUG 모드에서 dev user 반환하도록 수정 (기존엔 토큰 없을 때만 우회)
4. **match_memories SQL 함수 수정**: `memories.metadata @> filter` → `memories.user_id = (filter->>'user_id')::uuid` + `memories.source_type = filter->>'source_type'`으로 변경. user_id가 metadata가 아닌 top-level 컬럼이라 항상 0건 반환하던 버그 수정

---

## API 엔드포인트 전체 목록

```
GET     /health

POST    /api/v1/auth/login
POST    /api/v1/auth/signup
GET     /api/v1/auth/me

GET     /api/v1/memories
POST    /api/v1/memories
POST    /api/v1/memories/upload-pdf
POST    /api/v1/memories/backfill
GET     /api/v1/memories/{memory_id}
DELETE  /api/v1/memories/{memory_id}

POST    /api/v1/chat/sessions
GET     /api/v1/chat/sessions/{session_id}/history
POST    /api/v1/chat/sessions/{session_id}/messages    (SSE)

GET     /api/v1/search?q=...
GET     /api/v1/search/related/{memory_id}

GET     /api/v1/journals
POST    /api/v1/journals
POST    /api/v1/journals/generate-draft
POST    /api/v1/journals/review-questions
POST    /api/v1/journals/insights
POST    /api/v1/journals/related-memories

GET     /api/v1/digest/today
GET     /api/v1/digest/date/{date_str}

GET     /api/v1/graph?limit=200

GET     /api/v1/stats/overview
GET     /api/v1/stats/activity
GET     /api/v1/stats/timeline

GET     /api/v1/integrations/kakao/auth
GET     /api/v1/integrations/kakao/callback
GET     /api/v1/integrations/kakao/status
POST    /api/v1/integrations/kakao/send
POST    /api/v1/integrations/kakao/disconnect
```

## Frontend 라우트

| 경로 | 뷰 | 상태 |
|------|-----|------|
| `/` | DashboardView | ✅ |
| `/login` | AuthView | ⚠️ DEV bypass |
| `/chat` | ChatView | ✅ |
| `/memories` | MemoryView | ✅ |
| `/journal` | JournalView | ✅ (AI 초안 생성 구현 완료) |
| `/search` | SearchView | ✅ |
| `/graph` | GraphView | ✅ (Neo4j 실데이터) |
| `/timeline` | TimelineView | ✅ |

---

## 개발 로드맵

> 수립일: 2026-02-09 | 1인 개발 + AI 에이전트 팀 기준
> 스프린트 단위: 1주 (부담 없이 진행 가능한 범위)
> 원칙: "수집 - 대화 - 저널 - 그래프" 핵심 루프 완성 우선

### 전체 타임라인 요약

```
Sprint 1 (Week 1) ── 그래프 인프라 + 실시간 스트리밍     ✅ 완료 (2026-02-09)
Sprint 2 (Week 2) ── Journal AI 초안 + Evening 플로우 완성  ✅ 완료 (2026-02-09)
Sprint 3 (Week 3) ── Graph-Chat 연동 + 하이브리드 RAG      ✅ 완료 (2026-02-09)
Sprint 4 (Week 4) ── 수집 확장 (KakaoTalk IN + PDF)       ✅ 완료 (PDF 구현, KakaoTalk은 외부 채널 설정 필요)
Sprint 5 (Week 5) ── 보완 + 안정화                        ✅ 완료 (backfill + 에러핸들링 + graph 개선)
```

### 의존관계 다이어그램

```
[Sprint 1: Neo4j 복구]
        |
        +---> [Sprint 3: Graph-Chat 연동 + 하이브리드 RAG]
        |
[Sprint 1: 실시간 스트리밍]
        |
        +---> [Sprint 2: Journal AI 초안 (evening 대화 기반)]

[Sprint 4: KakaoTalk IN + PDF] ── 독립 (의존성 없음)
[Sprint 5: 보완] ── Sprint 1~4 완료 후
```

---

### Sprint 1: 그래프 인프라 복구 + 실시간 스트리밍 (Week 1)

**목표**: 핵심 인프라 2개를 동시에 해결. 이후 스프린트의 선결 조건.

#### 1-A. Neo4j AuraDB 연결 복구 (P0)

| 항목 | 내용 |
|------|------|
| 현재 상태 | DNS 해석 실패. AuraDB 무료 인스턴스 만료/중지 상태 |
| 작업 내용 | (1) AuraDB 콘솔에서 인스턴스 상태 확인 및 재활성화 (또는 재생성) (2) `.env`의 `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` 업데이트 (3) `graph_repository.py`의 연결 로직 검증 (4) Librarian Save 노드에서 entity/relation -> Neo4j 저장 E2E 테스트 |
| 관련 파일 | `config/settings.py`, `.env`, `repositories/graph_repository.py`, `agents/librarian/nodes/save.py` |
| 리스크 | AuraDB Free Tier가 완전 삭제된 경우 데이터 유실. 재생성 시 빈 그래프에서 시작. 기존 메모리 재처리(backfill) 필요할 수 있음 |
| 기술 결정 | AuraDB Free Tier 유지 vs Docker 로컬 Neo4j vs Memgraph 등 대안 검토 |

#### 1-B. 실시간 토큰 스트리밍 (P1)

| 항목 | 내용 |
|------|------|
| 현재 상태 | `chat_service.py`에서 `socrates_graph.ainvoke()` 전체 응답 후 50자 청크 분할. UX가 느림 |
| 작업 내용 | (1) `socrates_node`에서 `llm.astream()` 사용으로 변경 (2) `chat_service.py`의 `send_message()`를 `astream_events()` 또는 직접 `async for chunk` 패턴으로 변경 (3) 프론트엔드 `ChatView`의 SSE 파싱 로직은 `data: {content: ...}` 형태이므로 BE만 수정하면 호환 |
| 관련 파일 | `services/chat_service.py`, `agents/socrates/nodes/chat.py`, `agents/socrates/graph.py` |
| 리스크 | LangGraph `astream_events()`의 이벤트 구조 파악 필요. 에러 발생 시 스트리밍 중간 끊김 처리 |
| 기술 결정 | LangGraph astream_events vs Socrates 노드를 직접 스트리밍 모드로 전환 |

**Sprint 1 완료 시 사용자 경험**:
- Chat에서 AI 응답이 토큰 단위로 실시간 출력됨 (체감 응답 속도 대폭 개선)
- Graph 페이지에서 실제 지식 그래프 데이터가 표시됨 (mock 데이터 탈피)
- 새 메모리 저장 시 자동으로 그래프에 entity/relation 반영

---

### Sprint 2: Journal AI 초안 생성 + Evening 플로우 (Week 2)

**목표**: "저녁 대화 -> 저널 초안 자동 생성" 핵심 UX 구현

**선결 조건**: Sprint 1-B (실시간 스트리밍) - evening 모드 대화가 자연스러워야 초안 품질 향상

#### 2-A. Evening 대화 -> Journal 초안 생성 (P0)

| 항목 | 내용 |
|------|------|
| 현재 상태 | `journal_service.py`에 AI 초안 생성 로직 없음. evening 모드 대화는 동작하지만 대화 내용이 저널로 연결되지 않음 |
| 작업 내용 | (1) `chat_service.py`에 evening 세션 대화 내역 추출 메서드 추가 (2) `journal_service.py`에 `generate_draft_from_evening()` 메서드 구현 -- evening 대화 히스토리를 LLM에 전달, 저널 초안 생성 (3) 새 API 엔드포인트: `POST /api/v1/journals/generate-draft` (session_id 받아서 해당 evening 대화 기반 초안 반환) (4) FE `JournalView`에 "AI 초안 생성" 버튼 추가 -- evening 세션 선택 -> 초안 로드 -> 편집 가능 |
| 관련 파일 | `services/journal_service.py`, `services/chat_service.py`, `routers/v1/journal_router.py`, FE `JournalView.tsx` |
| 데이터 흐름 | evening 대화 시작 -> 사용자와 AI가 하루 회고 -> 대화 종료 후 "저널로 정리" 클릭 -> LLM이 대화 내용 기반 초안 생성 -> 사용자가 편집/저장 |

#### 2-B. Digest date 필터 수정 (P2, 보너스)

| 항목 | 내용 |
|------|------|
| 현재 상태 | `digest_router.py`의 `/date/{date_str}` 엔드포인트가 `get_today_digest()` 호출 (TODO 상태) |
| 작업 내용 | `digest_service.py`에 `get_digest_by_date(date)` 메서드 추가. 날짜 파라미터를 받아 해당 날짜 기준 필터링 |
| 관련 파일 | `services/digest_service.py`, `routers/v1/digest_router.py` |

**Sprint 2 완료 시 사용자 경험**:
- 저녁에 evening 모드로 AI와 하루 회고 대화 후, "저널로 정리" 버튼으로 AI 초안 생성
- 초안을 편집하고 저장하면 성찰 질문 + 인지왜곡 분석까지 자동 연결
- **핵심 루프 "대화 -> 저널" 구간이 완성됨**

---

### Sprint 3: Graph-Chat 연동 + 하이브리드 RAG (Week 3)

**목표**: 지식 그래프와 대화 시스템을 연결. 핵심 루프의 "그래프 -> 대화" 구간 완성.

**선결 조건**: Sprint 1-A (Neo4j 연결 복구)

#### 3-A. Graph -> Chat 연동 (P0)

| 항목 | 내용 |
|------|------|
| 현재 상태 | `GraphView`에서 노드 클릭 시 아무 동작 없음. 그래프와 채팅이 분리된 상태 |
| 작업 내용 | (1) FE: `GraphView`에서 노드 클릭 시 해당 topic을 query param으로 ChatView에 전달 (예: `/chat?topic=React&mode=insight`) (2) BE: `POST /api/v1/chat/sessions` 에 `initial_topic` 파라미터 추가. 세션 생성 시 초기 컨텍스트로 주입 (3) Socrates 노드에서 `context.topic`이 있으면 해당 주제의 관련 메모리를 우선 검색 |
| 관련 파일 | FE: `GraphView.tsx`, `ChatView.tsx`. BE: `chat_service.py`, `routers/v1/chat_router.py` |

#### 3-B. 하이브리드 RAG (벡터 + 그래프 Traversal) (P1)

| 항목 | 내용 |
|------|------|
| 현재 상태 | `socrates_node`에서 `vector_repo.similarity_search()` 만 사용. 그래프 컨텍스트 없음 |
| 작업 내용 | (1) `graph_repository.py`에 `get_related_context(topic, depth=2)` 추가 -- 특정 entity에서 2-hop 이내 연결된 노드/관계 조회 (2) `socrates_node`에서 벡터 검색 결과 + 그래프 traversal 결과를 합쳐서 system prompt에 주입 (3) 그래프 컨텍스트 형식: "Knowledge Graph에 따르면, [X]는 [Y]와 RELATED_TO 관계이며, [Z]에 DEPENDS_ON 합니다" |
| 관련 파일 | `repositories/graph_repository.py`, `agents/socrates/nodes/chat.py` |
| 리스크 | Neo4j 쿼리 응답 시간이 SSE 스트리밍 지연에 영향. Cypher 쿼리 최적화 필요 |

**Sprint 3 완료 시 사용자 경험**:
- 그래프에서 "React" 노드 클릭 -> ChatView로 이동 -> AI가 React 관련 메모리와 그래프 연결 관계를 기반으로 대화
- AI 대화 시 "지식 그래프에 따르면 React는 Frontend, Web과 연결되어 있고, 지난주 저장한 [React 18 Features]와 관련됩니다"와 같은 맥락 있는 응답
- **핵심 루프 "그래프 -> 대화" 구간이 완성됨. 전체 사이클 완성.**

---

### Sprint 4: 수집 채널 확장 (Week 4)

**목표**: 입력 채널 다양화. 카카오톡과 PDF로 수집 범위 확대.

**선결 조건**: 없음 (독립적. Sprint 1~3과 병행 가능하나 우선순위상 뒤로 배치)

#### 4-A. KakaoTalk IN - 채널 봇 수신 (P1)

| 항목 | 내용 |
|------|------|
| 현재 상태 | 카카오 OUT(나에게 보내기)은 구현됨. IN(사용자 -> 채널)은 미구현 |
| 작업 내용 | (1) 카카오 비즈니스 채널 생성 (Kakao Developers 콘솔) (2) 챗봇 웹훅 URL 설정: `POST /api/v1/integrations/kakao/webhook` (3) 웹훅 수신 -> 메시지 파싱 -> Librarian 파이프라인으로 메모리 저장 (4) 응답: 저장 완료 알림을 채널 봇으로 회신 |
| 관련 파일 | `services/kakao_service.py`, `routers/v1/integrations_router.py` |
| 리스크 | 카카오 비즈니스 채널 승인 절차 소요 시간 불확실. 개발용 테스트 채널은 비교적 빠름 |
| 기술 결정 | 카카오 스킬 서버 방식 vs 플러스친구 API 방식 선택 |

#### 4-B. PDF 파싱 구현 (P2)

| 항목 | 내용 |
|------|------|
| 현재 상태 | Upstage API 키는 `.env`에 있으나, 엔드포인트가 501 반환 |
| 작업 내용 | (1) `memory_service.py` 또는 별도 `pdf_service.py`에서 Upstage Document Parse API 호출 (2) PDF 내용 추출 -> Librarian 파이프라인에 source_type=PDF로 전달 (3) FE: Memory 생성 화면에 PDF 업로드 UI 추가 |
| 관련 파일 | `services/memory_service.py`, `routers/v1/memory_router.py` |

**Sprint 4 완료 시 사용자 경험**:
- 카카오톡에서 채널 봇에게 메시지/링크를 보내면 자동으로 메모리에 저장
- PDF 파일을 업로드하면 내용 추출 -> 요약 -> 태깅 -> 그래프 반영까지 자동 처리
- **수집 채널이 웹/노트/카카오톡/PDF 4가지로 확대**

---

### Sprint 5: 안정화 + 보완 (Week 5)

**목표**: 전체 플로우 점검, 엣지 케이스 처리, UX 개선

| 작업 | 우선순위 | 설명 |
|------|---------|------|
| Supabase Auth 키 정상화 | P3 | `sb_secret_` -> `eyJ...` JWT 형식 확인. Supabase 대시보드에서 실제 service_role_key 재확인 |
| 에러 핸들링 강화 | P2 | Neo4j 연결 끊김 시 자동 fallback, LLM 타임아웃 처리, SSE 연결 끊김 복구 |
| 그래프 backfill | P1 | 기존 메모리(Neo4j 미연결 시 저장된 것들)를 그래프에 일괄 반영하는 스크립트 |
| UX 개선 | P2 | Dashboard에서 evening 모드 바로가기, 저널 초안 상태 표시, 그래프 줌/필터 |
| 성능 모니터링 | P3 | Librarian 파이프라인 처리 시간 로깅, LLM API 비용 추적 |

**Sprint 5 완료 시 사용자 경험**:
- 안정적으로 전체 사이클을 반복 사용 가능
- 과거에 저장했던 메모리들도 그래프에 반영되어 풍부한 지식 네트워크 형성
- 에러 상황에서도 graceful degradation으로 서비스 지속

---

### 리스크 레지스터

| ID | 리스크 | 영향 | 대응 방안 |
|----|--------|------|----------|
| R1 | AuraDB Free Tier 완전 삭제 | 높음 - Sprint 1, 3 블로킹 | Docker 로컬 Neo4j로 전환 (`docker run neo4j:5`). 개발 단계에서는 로컬이 더 안정적일 수 있음 |
| R2 | OpenAI API 비용 증가 | 중간 - 스트리밍 + 하이브리드 RAG로 호출 증가 | 캐싱 전략 도입. 반복 질문은 임베딩 유사도로 기존 응답 재활용 |
| R3 | LangGraph astream_events 호환성 | 낮음 - 스트리밍 구현 복잡도 | 대안: LangGraph 우회하고 `chat.py`에서 직접 `llm.astream()` 호출 후 SSE 전달 |
| R4 | 카카오 비즈니스 채널 승인 지연 | 중간 - Sprint 4 일정 지연 | 개발 단계에서는 테스트 채널로 진행. 프로덕션 전환 시 정식 승인 |
| R5 | Supabase Auth 키 문제 | 낮음 - DEBUG 모드로 우회 중 | 프로덕션 전환 전에 반드시 해결 필요 |

### 기술 결정 필요 사항 (ADR 후보)

| 결정 사항 | 선택지 | 판단 기준 | 권장안 |
|----------|--------|----------|--------|
| Neo4j 호스팅 | AuraDB Free vs Docker 로컬 vs Memgraph | 안정성, 비용, 운영 부담 | 개발: Docker 로컬 / 프로덕션: AuraDB |
| 스트리밍 구현 | LangGraph astream_events vs 직접 llm.astream | 구현 복잡도, 유지보수 | LangGraph 우회하여 직접 스트리밍 (더 단순) |
| Journal 초안 생성 트리거 | 자동(evening 세션 종료 시) vs 수동(버튼 클릭) | UX 자연스러움, 비용 | 수동 (사용자가 원할 때 생성. API 비용 절약) |
| 하이브리드 RAG 전략 | 벡터 우선 + 그래프 보강 vs 그래프 우선 + 벡터 보강 | 응답 품질, 지연 시간 | 벡터 우선 + 그래프 보강 (벡터가 이미 안정적) |

---

## 아키텍처 메모

- **계층 구조**: Router → Service → Repository → DB
- **DI**: FastAPI Depends() 사용, `config/dependencies.py`에서 의존성 팩토리 관리
- **Agents**: LangGraph 기반
  - Librarian: 콘텐츠 처리 (Curator→Ontologist→Save)
  - Socrates: 대화 (4개 모드, 벡터 RAG)
- **Graph Graceful Degradation**: Neo4j 미연결 시 Supabase tags 기반 mock 그래프 반환
- **Supabase Client**: service_role_key 사용 → RLS 우회. match_memories 등 RPC에서 user_id 직접 필터링 필요
