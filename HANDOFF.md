# Memorial 프로젝트 인수인계 문서

## 📋 프로젝트 개요

**Memorial**은 AI 기반 지식 관리 시스템(Digital Second Brain)입니다.

### 핵심 기능
1. **Memory 저장**: 웹 페이지, PDF, 노트 등을 벡터 DB에 저장
2. **Socrates Agent**: 저장된 지식 기반 대화형 AI
3. **Knowledge Graph**: 개념 간 연관관계 시각화
4. **Journal System**: AI 기반 일기 작성 + 회고 질문 생성
5. **Daily Digest**: 오늘 수집한 자료 요약 + AI 질문

---

## 🏗️ 기술 스택

### Backend
| 기술 | 용도 |
|------|------|
| **FastAPI** | REST API 서버 |
| **LangChain** | LLM 오케스트레이션, Agent 구현 |
| **Supabase** | PostgreSQL + Vector Store (pgvector) |
| **Neo4j** (Optional) | Knowledge Graph 저장소 |
| **OpenAI GPT-4o** | LLM 모델 |

### Frontend
| 기술 | 용도 |
|------|------|
| **React 18** | UI 프레임워크 |
| **Vite** | 빌드 도구 |
| **TypeScript** | 타입 안전성 |
| **react-force-graph-2d** | Graph 시각화 |
| **react-markdown** | Markdown 렌더링 |

---

## 📁 프로젝트 구조

```
memorial/
├── backend/
│   ├── app/
│   │   ├── agents/           # AI Agents
│   │   │   ├── librarian/    # 자료 처리 Agent
│   │   │   └── socrates/     # 대화 Agent
│   │   ├── routers/v1/       # API 엔드포인트
│   │   ├── services/         # 비즈니스 로직
│   │   ├── repositories/     # 데이터 접근 계층
│   │   └── config/           # 설정
│   └── docs/                 # 스키마 문서
├── frontend/
│   ├── src/
│   │   ├── components/       # React 컴포넌트
│   │   └── App.tsx           # 메인 앱
│   └── vite.config.ts
└── .env                      # 환경변수
```

---

## 🔌 API 엔드포인트

### Memory
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/memories` | 메모리 생성 |
| GET | `/api/v1/memories` | 메모리 목록 |
| GET | `/api/v1/memories/{id}` | 메모리 상세 |
| DELETE | `/api/v1/memories/{id}` | 메모리 삭제 |

### Chat (Socrates Agent)
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/chat` | 채팅 메시지 전송 |
| GET | `/api/v1/chat/sessions` | 세션 목록 |
| GET | `/api/v1/chat/sessions/{id}/messages` | 메시지 히스토리 |

### Journal
| Method | Endpoint | 설명 |
|--------|----------|------|
| POST | `/api/v1/journals` | 일기 저장 |
| GET | `/api/v1/journals` | 일기 목록 |
| POST | `/api/v1/journals/insights` | 인지적 왜곡 분석 |
| POST | `/api/v1/journals/review-questions` | 회고 질문 생성 |
| POST | `/api/v1/journals/related-memories` | 관련 메모리 조회 |

### Graph
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/graph` | 그래프 시각화 데이터 |

### Stats & Digest
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/stats/overview` | 대시보드 통계 |
| GET | `/api/v1/stats/activity` | 일별 활동 데이터 |
| GET | `/api/v1/digest/today` | 오늘의 다이제스트 |

### Search
| Method | Endpoint | 설명 |
|--------|----------|------|
| GET | `/api/v1/search` | 통합 검색 |

---

## 🔧 환경 설정

### 필수 환경변수 (.env)
```bash
# Supabase
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=your-service-key

# OpenAI
OPENAI_API_KEY=sk-xxx

# Neo4j (Optional)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
```

### 실행 방법
```bash
# Backend
cd backend
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

---

## 🚀 미완료 작업 (Kakao Bot)

### 1. Kakao Bot Integration
- **목적**: 카카오톡으로 링크/메모 전송 → Memorial 자동 저장
- **필요사항**: 
  - 카카오 비즈니스 계정
  - OpenBuilder 스킬 설정
- **구현 위치**: `backend/app/services/kakao.py` (미완성)

### 구현 가이드
1. 카카오 OpenBuilder에서 스킬 생성
2. Webhook URL: `POST /api/v1/integrations/kakao/webhook`
3. 메시지 파싱 → Librarian Agent 호출 → Memory 저장

---

## 📊 데이터 모델

### Memory
```typescript
{
  id: UUID,
  title: string,
  content: string,
  summary: string,
  url?: string,
  source_type: "WEB" | "PDF" | "NOTE" | "CHAT",
  tags: string[],
  embedding: vector(1536),
  created_at: timestamp
}
```

### Journal
```typescript
{
  id: UUID,
  user_id: UUID,
  content: string,
  mood: "POSITIVE" | "NEUTRAL" | "NEGATIVE",
  sentiment_score: float,
  created_at: timestamp
}
```

---

## 🔍 주요 구현 세부사항

### 1. Vector Search
- **위치**: `services/search_service.py`
- **기술**: Supabase pgvector + OpenAI Embeddings
- **사용**: Memory 검색, Related Memories

### 2. Socrates Agent
- **위치**: `agents/socrates/`
- **특징**: LangGraph 기반 StateGraph
- **모드**: 일반 대화, Counter-argument, Insight Prompting

### 3. Graph Visualization
- **Backend**: `routers/v1/graph.py` - 동적 그래프 생성
- **Frontend**: `components/GraphView.tsx` - react-force-graph-2d

### 4. Daily Digest
- **Backend**: `services/digest_service.py`
- **기능**: 오늘의 Memory/Journal 집계 + AI 질문 생성

---

## 📝 코드 스타일

- **Backend**: Python 3.11+, Type Hints, async/await
- **Frontend**: TypeScript, Functional Components, CSS Modules
- **API**: RESTful, FastAPI Depends DI

---

## 🐛 알려진 이슈

1. **Neo4j 연결 경고**: `langchain-neo4j` 패키지로 마이그레이션 필요
2. **브라우저 테스트**: 로컬 환경에서 browser subagent 연결 불안정

---

## 📞 추가 참조

- `walkthrough.md`: 구현 세부 기록
- `implementation_plan.md`: 초기 설계 문서
- `task.md`: 작업 체크리스트
