# Memoir 코드 컨벤션

## 디렉토리 구조

### 프론트엔드 (`frontend/src/`)

```
src/
├── api/            # API 클라이언트 모듈 (도메인별 분리)
│   ├── client.ts   # 공통 HTTP 메서드 + 인증 + 재시도 로직
│   ├── memories.ts # 메모리 CRUD API
│   ├── chat.ts     # 채팅 + SSE 스트리밍
│   └── index.ts    # 배럴 export
├── components/     # React 컴포넌트
│   ├── dashboard/  # DashboardView 서브 컴포넌트
│   ├── graph/      # GraphView 서브 컴포넌트 + 상수
│   ├── journal/    # JournalView 서브 컴포넌트
│   ├── memory/     # MemoryView 서브 컴포넌트
│   ├── settings/   # SettingsView 서브 컴포넌트
│   ├── shared/     # 공용 컴포넌트 (SourceIcon 등)
│   └── demo/       # 데모 모드 전용 컴포넌트
├── contexts/       # React Context (AuthContext, ToastContext)
├── hooks/          # 커스텀 훅 (useMemoryList, useBulkSelection 등)
├── lib/            # 외부 라이브러리 초기화 (Supabase, Tiptap)
├── types/          # TypeScript 타입 정의
└── utils/          # 유틸리티 함수 (date, format)
```

### 백엔드 (`backend/app/`)

```
app/
├── agents/         # LangGraph 에이전트
│   ├── librarian/  # Librarian 에이전트 (메모리 저장/검색)
│   └── socrates/   # Socrates 에이전트 (대화형 AI)
├── config/         # 설정 + DI 컨테이너
│   ├── database.py # Supabase 클라이언트 초기화
│   └── dependencies.py # FastAPI Depends 팩토리 (Repository → Service)
├── repositories/   # 데이터 액세스 계층 (Supabase/KuzuDB 쿼리)
├── routers/        # FastAPI 라우터 (엔드포인트 정의)
├── schemas/        # Pydantic 요청/응답 스키마
├── services/       # 비즈니스 로직 계층
└── utils/          # 유틸리티 (임베딩, 텍스트 처리)
```

## 파일 네이밍

| 위치 | 규칙 | 예시 |
|------|------|------|
| 컴포넌트 | PascalCase | `MemoryAllTab.tsx`, `GraphLegend.tsx` |
| 커스텀 훅 | `use` + PascalCase | `useMemoryList.ts`, `useBulkSelection.ts` |
| 유틸리티 | camelCase | `date.ts`, `format.ts` |
| API 모듈 | camelCase (도메인명) | `memories.ts`, `chat.ts` |
| 백엔드 | `{도메인}_{계층}.py` | `memory_service.py`, `chat_repository.py` |
| 테스트 | `test_{대상}.py` / `{대상}.test.ts` | `test_memory_service.py`, `date.test.ts` |

## 컴포넌트 분리 기준

- **300줄 이상**: 서브 컴포넌트 + 커스텀 훅 분리 검토
- **분리 패턴**: View(오케스트레이터) → 탭/패널별 서브 컴포넌트 + 상태 관리 훅
- **CSS 클래스명**: 분리 시에도 기존 클래스명 유지 (CSS 파일 수정 최소화)

## import 순서

```tsx
// 1. React/라이브러리
import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'

// 2. 외부 아이콘/UI 라이브러리
import { Plus, X } from 'lucide-react'

// 3. 내부 context/API/타입
import { useToast } from '../contexts/ToastContext'
import { fetchMemories } from '../api'
import type { Memory } from '../types'

// 4. 내부 컴포넌트/훅
import MemoryAllTab from './memory/MemoryAllTab'
import { useMemoryList } from '../hooks/useMemoryList'

// 5. CSS
import './MemoryView.css'
```

## 에러 핸들링

### 프론트엔드
- API 호출: `client.ts`의 공통 메서드가 `ApiResponseError`로 변환
- 컴포넌트: try-catch → `toast.error()` 패턴
- SSE 스트림: `readSSEStream()`에서 청크 단위 에러 처리

### 백엔드
- 라우터: `HTTPException` 직접 raise
- 서비스: 비즈니스 예외를 상위로 전파
- 리포지토리: Supabase 쿼리 실패 시 예외 raise

## 테스트

### 백엔드 (pytest)
- `MagicMock` / `AsyncMock`으로 의존성 모킹
- `@pytest.mark.asyncio` 비동기 테스트
- 파일: `backend/tests/test_{서비스명}.py`

### 프론트엔드 (vitest)
- 순수 함수 유닛 테스트 우선
- 파일: `src/{모듈}/__tests__/{대상}.test.ts`
- 실행: `npm run test:unit`

## 기타 규칙

- 모든 주석/독스트링은 **한국어**
- 파일 레벨 독스트링은 사용하지 않음 (함수/클래스 독스트링만 허용)
- 커밋 메시지: `타입: 핵심 요약` (한국어 본문)
- Co-Authored-By 라인 추가하지 않음
