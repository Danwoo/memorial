# Memoir AI - 프로젝트 구조 및 디자인 패턴 (Project Structure & Patterns)

"코드를 짜는 것보다, 코드를 둘 자리를 정하는 것이 더 중요합니다."
유지보수와 확장성을 "1순위"로 고려한 **Standard Scaffolding Strategy**를 제안합니다.

---

## 2. Directory Structure (Monorepo-style)
루트에서 프론트/백엔드/문서를 한눈에 관리하는 구조입니다.

```text
memorial/
├── docs/                     # [Documentation] 설계 문서 모음 (PRD, Spec 등)
├── docker-compose.yml        # [Clean] 로컬 실행 한방 코드
├── .env.example              # [Security] 환경변수 템플릿
├── README.md                 # 프로젝트 대문
│
├── frontend/                 # [React + Vite]
│   ├── Dockerfile
│   ├── src/
│   │   ├── app/              # (Optional) Routing / Global Layout
│   │   ├── components/       # [Shared] 공통 UI 컴포넌트 (Button, Input..)
│   │   ├── features/         # [★ Key Pattern] 기능 단위 격리
│   │   │   ├── auth/         # 인증 관련 (Login, ProtectedRoute)
│   │   │   ├── memory/       # 메모리 CRUD, 카드 UI
│   │   │   ├── graph/        # 2D/3D 그래프 시각화 로직
│   │   │   └── chat/         # 채팅, 소켓, 메시지 UI
│   │   ├── lib/              # [Utils] API Client, Constants
│   │   ├── hooks/            # [Global Hooks]
│   │   └── stores/           # [Global State] Zustand/Jotai
│   └── ...config files
│
└── backend/                  # [FastAPI + Python]
    ├── Dockerfile
    ├── poetry.lock / pyproject.toml
    └── app/
        ├── main.py           # Entrypoint
        ├── api/              # [Interface Layer]
        │   └── v1/           # API Versioning
        │       ├── endpoints/
        │       └── api.py
        ├── core/             # [Config] Settings, Security, Event Handlers
        ├── agents/           # [Multi-Agent System] ★ LangGraph Logic
        │   ├── state.py      # Shared Architecture State
        │   ├── librarian/    # [Background] Knowledge Curator
        │   │   ├── graph.py  # Subgraph Definition
        │   │   └── nodes/    # ★ Internal Specialist Nodes
        │   │       ├── curator.py    # Value Check & Classification
        │   │       └── ontologist.py # Entity & Relation Extraction
        │   │   └── tools.py
        │   ├── socrates/     # [Foreground] User Interface
        │   │   ├── graph.py
        │   │   └── tools.py
        │   └── tools/        # Shared Tools (Graph, Search...)
        ├── services/         # [Business Logic Layer]
        │   ├── ingest_service.py # [Core Pipeline] PDF/Web Parsing (No Agent)
        │   ├── agent_service.py  # LangGraph 실행기
        │   └── sync_service.py   # RDB <-> Graph Consistency
        ├── crud/             # [Data Access Layer] DB 쿼리 전담
        │   ├── crud_memory.py
        │   └── crud_user.py
        ├── schemas/          # [DTO] Pydantic Models (Request/Response)
        └── models/           # [DB] SQLAlchemy / SQLModel (Optional)
```

---

## 2. Design Patterns (Architecture Decision)

### 2.1 Frontend Pattern: **"Feature-Sliced Design (Light)"**
*   **문제**: 보통 `components`, `pages`로 나누면, 나중에 "메모" 관련 코드가 10군데로 흩어져서 수정하다가 파일 찾느라 시간 다 씁니다.
*   **해결책 (Features)**: 관련된 코드를 **기능(`features`)별로 뭉쳐놓습니다.**
    *   `features/graph/components`: 그래프 그리는 컴포넌트
    *   `features/graph/api.ts`: 그래프 API 호출 함수
    *   `features/graph/hooks.ts`: 그래프 로직 훅
    *   *효과*: "그래프 고쳐야지" 하면 `features/graph` 폴더만 보면 됩니다. (응집도 상승)

### 2.2 Backend Pattern: **"Layered Architecture (Service Pattern)"**
*   **문제**: `api/endpoints/memory.py` 파일 하나에 DB쿼리, 비즈니스 로직, API 응답이 다 섞이면 "스파게티 코드"가 됩니다.
*   **해결책**: 철저하게 **3단 분리**합니다.
    1.  **Router (API)**: "요청이 오면 Service를 부르고, 결과를 Pydantic으로 포장해서 보낸다." (로직 없음)
    2.  **Service (Business)**: "LLM한테 물어보고, Graph DB에 넣고, 실패하면 재시도한다." (순수한 파이썬 로직)
    3.  **CRUD (Data)**: "DB에서 가져온다. 저장한다." (SQL/Query만 존재)
    *   *효과*: DB를 바꿔도 Service는 안 고쳐도 됨. API 프레임워크를 바꿔도 Service는 그대로 씀.

---

## 3. Documentation Strategy
기존에 작성된 `*.md` 파일들을 `memorial/docs/` 폴더로 이동하여 체계적으로 관리합니다.
*   `memorial/docs/01_PRD.md`
*   `memorial/docs/02_Tech_Spec.md`
*   `memorial/docs/03_Data_Schema.md`
*   `memorial/docs/04_API_Spec.md`
*   `memorial/docs/05_Project_Structure.md`
*   `memorial/docs/06_Agent_Architecture.md`
*   `memorial/docs/07_Agent_Design_Spec.md` (New)

이 구조대로 폴더를 생성하고 파일을 정리해도 되겠습니까?
