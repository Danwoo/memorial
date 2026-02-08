# Memoir AI

> **"단순 기록(Record)이 아닌, 자산(Asset)으로의 전환"**

지능형 인지 장부 - 매일 소비되는 휘발성 정보를 사용자의 주관적 맥락과 결합하여,
시간이 흐를수록 가치가 높아지는 **개인화된 지식 온톨로지**를 구축합니다.

---

## 🚀 Quick Start

### Backend (FastAPI)
```bash
cd backend
poetry install
poetry run uvicorn app.main:app --reload
```

### Frontend (React + Vite)
```bash
cd frontend
npm install
npm run dev
```

---

## 📁 Project Structure
```
memorial/
├── docs/          # 설계 문서 (PRD, Tech Spec, API Spec...)
├── frontend/      # React + Vite + TypeScript
├── backend/       # FastAPI + LangGraph
│   └── app/
│       ├── agents/    # Librarian, Socrates Agents
│       ├── services/  # Ingest, Sync Services
│       └── ...
└── README.md
```

## 📚 Documentation
- [PRD (제품 요구사항)](./docs/01_PRD.md)
- [Tech Spec (기술 명세서)](./docs/02_Tech_Spec.md)
- [Data Schema](./docs/03_Data_Schema.md)
- [API Spec](./docs/04_API_Spec.md)
- [Agent Architecture](./docs/06_Agent_Architecture.md)

---

## 🛠️ Tech Stack
- **Frontend**: React, Vite, TypeScript
- **Backend**: Python, FastAPI, LangGraph
- **Database**: Supabase (Postgres + pgvector), Neo4j
- **AI**: OpenAI GPT, LangChain
