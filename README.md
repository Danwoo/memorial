# Memoir AI

AI 기반 개인 지식 관리(PKM) 시스템. 읽고, 생각하고, 깨달은 것들을 AI와 함께 정리하는 **지능형 인지 장부**.

## 주요 기능

### 수집 (Memory)
- 웹 URL, 메모, PDF 저장 → AI 자동 분류/태그/요약
- 고급 검색 (태그, 소스, 날짜, 정렬) + 벡터 유사도 검색
- 중복 감지 및 병합, 일괄 관리

### 대화 (Chat with Socrates)
- 저장된 기억을 바탕으로 한 맥락 인식 AI 대화
- 실시간 스트리밍 응답 + 출처 참조 표시
- 사용자 프로필 기반 개인화 + 장기 맥락

### 회고 (Journal)
- 3-Panel 레이아웃: 날짜 목록 / Tiptap 에디터 / AI 회고 패널
- 서버 자동 저장 + @멘션 메모리 참조
- AI 회고 질문 + 일간 요약 초안

### 발견 (Knowledge Graph)
- 3D 지식 그래프 시각화 (react-force-graph)
- 클러스터/트렌드/허브/고립 노드 인사이트

### 대시보드
- 오늘의 브리핑 + 추천 질문 + 활동 히트맵
- 주간/월간 AI 리포트 + AI 인사이트

### 추가 기능
- 데모 모드 (`/demo`) — 비로그인 체험
- Ctrl+K 글로벌 검색 (`tag:`, `source:` 필터 문법)
- 데이터 내보내기 + PWA 오프라인 지원

---

## 기술 스택

| 구분 | 기술 |
|------|------|
| **Frontend** | React 18 + TypeScript + Vite |
| **Editor** | Tiptap (ProseMirror) |
| **3D Graph** | react-force-graph-3d / 2d |
| **Backend** | FastAPI + Python 3.11 |
| **AI Agent** | LangGraph (Socrates + Librarian) |
| **LLM** | OpenAI GPT-4o / GPT-4o-mini |
| **Database** | Supabase (PostgreSQL + pgvector) |
| **Graph DB** | KuzuDB |
| **Auth** | Supabase Auth (Google/Kakao OAuth) |
| **Deploy** | Fly.io (Backend) + Vercel (Frontend) |
| **CI** | GitHub Actions |

---

## 아키텍처

```
┌──────────────────┐     ┌──────────────────────────────────┐
│   React SPA      │────▶│   FastAPI Backend                 │
│   (Vercel)       │     │   (Fly.io)                        │
│                  │     │                                    │
│  Chat / Memory   │     │  ┌─────────────┐  ┌────────────┐ │
│  Journal / Graph │     │  │  Socrates    │  │  Librarian  │ │
│  Dashboard       │     │  │  (LangGraph) │  │  (LangGraph)│ │
│  Demo Mode       │     │  └─────────────┘  └────────────┘ │
└──────────────────┘     │         │                │        │
                         │    ┌────┴────────────────┴───┐    │
                         │    │  Supabase                │    │
                         │    │  PostgreSQL + pgvector   │    │
                         │    └─────────────────────────┘    │
                         │    ┌─────────────────────────┐    │
                         │    │  KuzuDB (Graph)         │    │
                         │    └─────────────────────────┘    │
                         └──────────────────────────────────┘
```

---

## 로컬 개발

### 필수 요구사항
- Node.js 20+, Python 3.11+, uv
- Supabase 프로젝트 (PostgreSQL + pgvector)
- OpenAI API Key

### Frontend
```bash
cd frontend
npm install
npm run dev          # http://localhost:5173
```

### Backend
```bash
cd backend
uv sync
cp .env.example .env  # 환경변수 설정
uv run uvicorn app.main:app --reload  # http://localhost:8000
```

### 환경변수 (Backend `.env`)
```
OPENAI_API_KEY=sk-...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=eyJ...
SUPABASE_SERVICE_ROLE_KEY=eyJ...
KUZU_DB_PATH=./kuzu_data
```

---

## 개발 컨벤션

| 항목 | 규칙 |
|------|------|
| Backend 패키지 관리 | `uv` (pip/python 직접 사용 금지) |
| Backend Lint | `ruff check --fix` + `ruff format` |
| Frontend Lint | `eslint --max-warnings=0` |
| Pre-commit | `.pre-commit-config.yaml` (ruff + eslint 자동 적용) |
| Commit 메시지 | 한국어 |

---

## 프로젝트 구조

```
memorial/
├── frontend/               # React SPA
│   ├── src/
│   │   ├── components/     # 뷰 컴포넌트 (26+)
│   │   ├── api/            # API 클라이언트 (13개)
│   │   ├── contexts/       # React Context (Auth, Theme, Toast, Demo)
│   │   ├── types/          # TypeScript 타입 (9개)
│   │   └── data/           # 데모 데이터
│   ├── e2e/                # Playwright E2E 테스트
│   └── public/             # 정적 에셋
├── backend/
│   └── app/
│       ├── routers/        # API 라우터 (14개)
│       ├── services/       # 비즈니스 로직 (16개)
│       ├── repositories/   # 데이터 접근 (8개)
│       ├── schemas/        # Pydantic 스키마 (13개)
│       ├── config/         # 설정/미들웨어/의존성
│       └── utils/          # 유틸리티 (캐시 등)
├── docs/                   # 설계 문서
├── .github/workflows/      # CI (GitHub Actions)
└── README.md
```

## 문서
- [PRD (제품 요구사항)](./docs/01_PRD.md)
- [Tech Spec (기술 명세서)](./docs/02_Tech_Spec.md)
- [Data Schema](./docs/03_Data_Schema.md)
- [API Spec](./docs/04_API_Spec.md)
- [Agent Architecture](./docs/06_Agent_Architecture.md)
