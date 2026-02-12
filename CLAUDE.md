# Memoir 프로젝트 규칙

## 작업 프로세스 (필수)

모든 작업은 **개발 → 검증 → 커밋** 순서로 진행한다.

### 1. 개발
- 코드 작성 완료 후 다음 단계로 진행

### 2. 검증 (필수)
다음 항목을 **모두** 수행해야 커밋 가능:

#### 정적 검증
- **TypeScript 타입 체크**: `cd frontend && npx tsc --noEmit`
- **프론트엔드 빌드**: `cd frontend && npm run build`
- **Python 구문 검증**: `python -c "import ast; ast.parse(open('파일경로', encoding='utf-8').read())"`

#### 동작 검증 (실제 실행)
- **프론트엔드**: `cd frontend && npm run dev` 실행 후 브라우저에서 기능 동작 확인
- **백엔드**: `cd backend && uvicorn app.main:app --reload` 실행 후 API 동작 확인
- **통합 테스트**: 프론트-백엔드 연동 시나리오 실행

**검증 없이 커밋하지 않는다.** 반드시 로컬에서 실제 동작을 확인한다.

### 3. 커밋
검증이 완료된 후에만 커밋한다.

#### 커밋 메시지 규칙
- **형식**: `타입: 작업 핵심 요약 (P0-N, P1-N)`
- **타입**: `feat`, `fix`, `style`, `refactor`
- **본문**: 변경사항을 구체적으로 나열 (한국어)
- **Co-Authored-By 라인 절대 추가하지 않는다**
- **CLAUDE.md 수정 내용은 커밋 메시지에 언급하지 않는다**

#### 예시
```
fix: 벡터 검색 user_id 필터 추가 + 글로벌 토스트 시스템 + UX 개선

- 벡터 검색 보안 수정: Socrates 에이전트의 _search_vector_memories, find_contradicting_memories에 user_id 필터 전파하여 타 사용자 메모리 노출 방지
- 글로벌 토스트 시스템 구축: ToastContext 생성, success/error/info 3종 지원, 하단 중앙 표시, 3초 자동 소멸
- textarea 자동 높이 조절: ChatView 입력창에 scrollHeight 기반 auto-resize 적용 (max 200px)
- 모달 Escape 키 닫기: SessionPickerModal에 Escape 키보드 리스너 추가

(P0-1, P0-5, P0-7, P0-9)
```

## 코드 컨벤션
- 모든 주석/독스트링은 한국어로 작성한다
- 파일 레벨 독스트링은 사용하지 않는다 (함수/클래스 독스트링만 허용)

## 핵심 참조 문서
- `PRODUCT_REVIEW.md` — 제품 전략 및 문제점 목록 (v2.1, dogfooding 기준)
- `DEVELOPMENT_PLAN.md` — 스프린트 1/2 상세 개발 계획서
- `DESIGN_SPEC.md` — UI/UX 디자인 스펙 (NotebookLM 벤치마크)

## 현재 개발 단계
- **Phase 1 목표:** 파운더가 매일 사용할 수 있는 상태
- **스프린트 1 (P0):** 글로벌 토스트, 메모리 상세 모달, 보안 수정, textarea auto-resize, 새 대화 버튼, Escape 닫기, 환영 배너
- **스프린트 2 (P1):** glass-card 교체, 한국어화, 저널 AI 강화, 반응형, 접근성, Chat AI 자동 판단

## 아키텍처 요약
- **프론트엔드:** React 18 + TypeScript + Vite, Tiptap 에디터, react-force-graph-3d
- **백엔드:** FastAPI + LangGraph (Socrates/Librarian 에이전트), Supabase (PostgreSQL + pgvector), KuzuDB
- **인증:** Supabase JWT (Google/Kakao OAuth)
- **배포:** Fly.io (무료 티어)

## 보안 주의
- 벡터 검색 시 반드시 `user_id` 필터 적용 (chat.py Socrates 에이전트 누락 수정 필요)
