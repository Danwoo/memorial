# Memoir AI 프로젝트 회고

## 프로젝트 개요
- **기간**: 12 Sprint (~50일)
- **총 커밋**: 142+
- **목표**: AI 기반 개인 지식 관리(PKM) 시스템 — 모든 평가 항목 10/10 달성

---

## Sprint별 여정

### Sprint 1~3: 기초 구축
- Supabase + FastAPI + React 기본 구조
- 메모리 CRUD, 채팅 SSE 스트리밍
- LangGraph Socrates/Librarian 에이전트 초기 구현

### Sprint 4~5: 핵심 기능 확장
- KuzuDB 지식 그래프, 벡터 검색 (pgvector)
- 저널 시스템, 대시보드 통계
- 카카오 통합, 넛지 알림

### Sprint 6~7: 품질 강화
- PWA (manifest + 오프라인 폴백)
- 성능 최적화 (서버 캐시 + 코드 스플리팅)
- 데이터 내보내기, 랜딩 페이지
- ErrorBoundary, Rate Limiting, CORS

### Sprint 8: UX 기반 재정비
- 저널 3-panel 레이아웃 + Tiptap 에디터
- 메모리 상세 모달 + 메모리/채팅/대시보드 UX 개선
- Socrates 한국어 프롬프트 + 사용자 프로필 개인화
- 장기 맥락 + 피드백 시스템

### Sprint 9: Socrates 대화 완성 + 저널 심화
- 실시간 연결 제안, 품질 튜닝
- AI 능동 회고, 채팅 UX 완성도
- 한국어 요약 품질 개선

### Sprint 10: 지식 그래프 인사이트 + 대시보드 재설계
- 클러스터/트렌드/허브/고립 노드 분석 엔진
- 인사이트 패널 UI + 클러스터 시각화
- 대시보드 허브 레이아웃 (히어로 + 퀵 액션 + 히트맵)
- AI 인사이트 (패턴/연결/행동 제안)

### Sprint 11: 관리 체계 + 프로덕션 배포
- 고급 검색 필터/정렬 (6개 파라미터)
- 메모리 중복 감지 + 병합
- 주간/월간 AI 리포트
- Vercel + Fly.io 배포 구성, GitHub Actions CI

### Sprint 12: 완성
- API 콜드 스타트 자동 재시도
- Playwright E2E 테스트 4개 파일
- 데모 모드 (`/demo`) — 비로그인 체험
- README + 프로젝트 회고

---

## 기술 스택 평가

| 기술 | 평가 | 비고 |
|------|------|------|
| **FastAPI** | 매우 만족 | async + 타입 안전 + 자동 문서화 |
| **LangGraph** | 만족 | StateGraph 패턴이 에이전트 설계에 적합. 학습 곡선 존재 |
| **Supabase** | 만족 | PostgreSQL + pgvector + Auth 올인원. RLS 정책 편리 |
| **KuzuDB** | 보통 | 임베디드 그래프DB로 빠르지만 생태계 작음 |
| **React + TypeScript** | 만족 | 타입 안전성이 대규모 프로젝트에서 빛남 |
| **Tiptap** | 만족 | ProseMirror 기반 유연한 에디터. 커스터마이징 자유도 높음 |
| **react-force-graph** | 만족 | 3D 그래프 시각화가 인상적. WebGL 의존성이 번들 크기 증가 요인 |
| **Vite** | 매우 만족 | 빌드 속도 빠르고 HMR 안정적 |
| **Fly.io** | 만족 | 무료 티어 적절. 콜드 스타트 대응 필요 |

---

## 정량 지표

| 지표 | 값 |
|------|-----|
| Backend 라우터 | 14개 |
| Backend 서비스 | 16개 |
| Frontend 컴포넌트 | 30+개 |
| API 엔드포인트 | 50+개 |
| TypeScript 타입 파일 | 9개 |
| CSS 파일 | 15+개 |
| E2E 테스트 파일 | 4개 |

---

## 잘한 점

1. **Sprint 기반 점진적 개발**: 각 Sprint마다 검증 가능한 성과물 산출
2. **풀스택 일관성**: BE/FE를 항상 함께 구현하여 통합 이슈 최소화
3. **타입 안전성**: TypeScript + Pydantic으로 런타임 에러 대폭 감소
4. **검증 프로세스**: tsc + build + Python 구문 검증을 매 커밋 전 수행
5. **코드 스플리팅**: lazy import으로 초기 로딩 최적화
6. **데모 모드**: 비로그인 체험으로 프로덕트 접근성 향상

## 개선할 점

1. **테스트 커버리지**: E2E만 있고 단위 테스트 부족
2. **번들 사이즈**: GraphView 1.3MB — three.js 의존성 최적화 필요
3. **에러 복구**: 네트워크 오류 시 재시도는 추가했지만, 오프라인 큐 미구현
4. **접근성**: ARIA 속성 기본만 적용, 스크린 리더 테스트 미수행
5. **국제화**: 하드코딩 한국어, i18n 미적용

---

## 향후 로드맵

- 단위 테스트 추가 (pytest + vitest)
- GraphView 번들 최적화 (three.js tree-shaking)
- 오프라인 큐 + 동기화
- 모바일 네이티브 앱 (React Native)
- 다국어 지원 (i18n)
