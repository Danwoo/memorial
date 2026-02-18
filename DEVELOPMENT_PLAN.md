# Memoir 개발 계획서

**작성일:** 2026-02-12
**참석자:** PM, 백엔드 전문가, 프론트엔드 전문가, UI/UX 전문가
**기준 문서:** PRODUCT_REVIEW.md v2.1
**목표:** "파운더가 매일 사용할 수 있는 상태" 달성

---

## 1. 현재 상태 종합 진단

### 1.1 백엔드 (BE) — 완성도 높음

| 항목 | 상태 | 비고 |
|------|------|------|
| API 엔드포인트 | ✅ 28개 완성 | Memory CRUD, Chat SSE, Journal, Digest, Graph, Search, 카카오 연동 |
| 에이전트 시스템 | ✅ Socrates + Librarian | LangGraph 기반, RAG 검색, 엔티티 추출 |
| 인증 | ✅ Supabase JWT | `require_auth` + `get_user_id` 의존성 주입 |
| SSE 스트리밍 | ✅ 안정 동작 | `astream()` 토큰 단위 |
| DELETE 메모리 API | ✅ 이미 존재 | `DELETE /api/v1/memories/{memory_id}` (memory_router.py:251) |
| 저널 AI 기능 | ✅ 부분 존재 | review-questions, insights, generate-draft API 존재 |
| **보안 취약점** | ❌ **user_id 필터 누락** | Socrates 벡터 검색 2곳 (chat.py:131, 110) |

### 1.2 프론트엔드 (FE) — 기능은 있으나 UX 미완성

| 항목 | 상태 | 비고 |
|------|------|------|
| 5개 주요 뷰 | ✅ 동작 | Chat, Memory, Journal, Graph, Settings |
| 토스트 시스템 | ❌ 글로벌 없음 | Settings/Journal에 로컬 구현만 존재 |
| 메모리 상세 | ❌ 미구현 | 카드 클릭 시 무반응 |
| 새 대화 버튼 | ❌ 미구현 | Sidebar에 CTA 없음 |
| textarea auto-resize | ❌ 미구현 | 고정 1줄 |
| alert() 잔존 | ⚠️ 3곳 | AIPanel.tsx:24, AIBubbleMenu.tsx:73,76 |
| glass-card 잔존 | ⚠️ 5곳 | MemoryView.tsx 전역 |
| 모달 Escape | ❌ 미구현 | overlay 클릭만 가능 |

### 1.3 UI/UX — 토큰 시스템 우수, 접근성/반응형 미비

| 항목 | 상태 | 비고 |
|------|------|------|
| 디자인 토큰 | ✅ 90% 완성 | CSS 변수 체계 우수, 라이트/다크 이중 정의 |
| 아이콘 마이그레이션 | ✅ 100% 완료 | Lucide React 전환 완료 |
| ARIA 접근성 | ❌ 0% | aria-label, role 전무 |
| 반응형 | ⚠️ 30% | GraphView/SettingsView만 부분 대응 |
| 한/영 혼재 | ⚠️ Sidebar 영문 | Chat/Memories/Journal/Graph/Settings |
| GraphView CSS | ❌ 문제 | 하드코딩 색상 + glassmorphism 잔존 |
| Empty state | ✅ 체계적 | 모든 뷰에 빈 상태 처리 있음 |

---

## 2. 핵심 발견 — 회의 합의사항

### 2.1 백엔드는 이미 준비되어 있다

> **BE 전문가:** "DELETE 메모리 API가 이미 있고, 저널 review-questions/insights/generate-draft API도 존재한다. P0 작업 대부분은 프론트엔드가 기존 백엔드 API를 연결하는 작업이다. 백엔드 신규 작업은 벡터 검색 보안 수정(P0-9)과 채팅 세션 제목 자동 생성(P1-4) 정도."

### 2.2 프론트엔드가 병목이다

> **FE 전문가:** "JournalView는 이미 12개 이상 상태 변수를 관리하고 있다. 글로벌 토스트 시스템을 먼저 만들어야 나머지 모든 피드백 작업이 가능하다. 토스트 → catch 블록 연결 → 메모리 상세 모달 순서가 맞다."

### 2.3 GraphView CSS가 가장 큰 기술 부채다

> **UI/UX 전문가:** "GraphView.css는 `#0a0a0f` 하드코딩 + `backdrop-filter: blur()` 4곳 + 다크모드 고정이라 라이트모드에서 완전히 깨진다. glass-card는 index.css에서 이미 평평한 카드로 변환했는데 MemoryView가 여전히 클래스명을 쓰고 있어서 실질적 영향은 적다. 실제 문제는 GraphView."

### 2.4 저널 AI API는 있지만 프론트에서 안 쓰고 있다

> **PM:** "백엔드에 `POST /journals/review-questions`(성찰 질문), `POST /journals/generate-draft`(초안 생성) API가 이미 있다. JournalView의 AIPanel이 이걸 호출하고 있긴 한데, 더 적극적으로 활용해야 한다. P1-13(저널 AI 강화)은 백엔드 신규 API보다는 프론트엔드 UX 개선 + 기존 API 활용 강화가 핵심."

---

## 3. 개발 전략: 3-트랙 병렬 진행

```
┌─────────────────────────────────────────────────────────────────┐
│                    스프린트 1 (Week 1: P0)                       │
│                                                                 │
│  Track A (FE 기반)     Track B (FE UX)      Track C (BE)       │
│  ─────────────────     ─────────────────     ──────────────     │
│  Day 1-2:              Day 1:                Day 1:             │
│  글로벌 토스트 시스템    textarea auto-resize   벡터검색 보안수정  │
│                        Escape 키 닫기                           │
│  Day 2-3:              새 대화 버튼            (완료→P1 선행)    │
│  catch 블록 연결                                                │
│  + alert 교체          Day 3-5:                                 │
│  + 성공 피드백          메모리 상세 모달                          │
│                                                                 │
│  Day 5-6:              Day 6-7:                                 │
│  첫 방문 환영 배너      통합 QA                                  │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                    스프린트 2 (Week 2-3: P1)                     │
│                                                                 │
│  Track A (디자인)      Track B (기능)         Track C (BE+AI)   │
│  ─────────────────     ─────────────────     ──────────────     │
│  glass-card 교체       반응형 사이드바         Chat AI 자동판단  │
│  한국어화              JournalView 반응형     세션 제목 자동생성 │
│  CSS 변수 잔존분       저널 자동저장           저널 AI 강화      │
│  테마 자동전환          모달 focus trap+ARIA                     │
│  메시지 버블색          ARIA live region                        │
└─────────────────────────────────────────────────────────────────┘
```

---

## 4. 스프린트 1 상세 계획 (P0: 2026-02-12 ~ 2026-02-19)

### Day 1 (2/12) — 기반 + 보안

| 순서 | 작업 | 담당 | 예상 | 선행 | 상세 |
|------|------|------|------|------|------|
| **1** | 벡터 검색 user_id 보안 수정 (P0-9) | BE | 2h | 없음 | `chat.py:131` `_search_vector_memories()`와 `chat.py:110` `find_contradicting_memories()`에 `filters={"user_id": str(user_id)}` 추가. search_service.py는 이미 적용됨 |
| **2** | 글로벌 토스트 시스템 (P0-1) 시작 | FE | 4h | 없음 | `ToastContext` + `ToastProvider` + `useToast()` 훅 생성. success/error/info 3종. 하단 중앙, 3초 auto-dismiss |
| **3** | textarea auto-resize (P0-5) | FE | 2h | 없음 | `scrollHeight` 기반, max-height 200px. Track B 병렬 |

**Day 1 체크포인트:**
- [x] BE: 벡터 검색 보안 수정 완료 + 테스트
- [x] FE: ToastContext 코드 작성 완료
- [x] FE: textarea auto-resize 동작 확인

### Day 2 (2/13) — 토스트 완성 + 피드백 연결

| 순서 | 작업 | 담당 | 예상 | 선행 | 상세 |
|------|------|------|------|------|------|
| **4** | 토스트 시스템 완성 + App 래핑 | FE | 2h | #2 | Provider를 App 최상단에 래핑. JournalView/SettingsView 로컬 토스트를 글로벌로 마이그레이션 |
| **5** | 전체 catch 블록 토스트 연결 (P0-2) | FE | 3h | #4 | ChatView 2곳, MemoryView 3곳, JournalView 2곳 = 총 7+곳에 `toast.error()` 추가 |
| **6** | 메모리 추가 성공 피드백 (P0-3) | FE | 1h | #4 | `addMemory` 성공 시 `toast.success()` |
| **7** | alert() 전수 교체 (P0-4 일부) | FE | 1h | #4 | AIPanel.tsx:24, AIBubbleMenu.tsx:73,76 → `toast.error()` 또는 조건부 UI 변경 |

**Day 2 체크포인트:**
- [x] 모든 API 에러에 사용자 피드백 표시
- [x] alert() 0건
- [x] 메모리 추가 시 성공 토스트

### Day 3 (2/14) — 모달 + 새 대화

| 순서 | 작업 | 담당 | 예상 | 선행 | 상세 |
|------|------|------|------|------|------|
| **8** | 모달 Escape 키 닫기 (P0-7) | FE | 2h | 없음 | MemoryView 추가 모달, SessionPickerModal에 `keydown` Escape 리스너 |
| **9** | 사이드바 "새 대화" 버튼 (P0-6) | FE | 3h | 없음 | Sidebar.tsx nav 상단에 `+ 새 대화` 필 버튼. `navigate('/chat', { state: { newSession: true } })` |
| **10** | 메모리 상세 모달 시작 (P0-4) | FE | 4h | 없음 | `MemoryDetailModal` 컴포넌트 생성 시작. 제목, 요약, 태그, URL, 생성일 표시 |

**Day 3 체크포인트:**
- [x] Escape 키로 모든 모달 닫기 동작
- [x] 새 대화 버튼 클릭 → 새 세션 시작
- [x] 메모리 상세 모달 기본 레이아웃

### Day 4-5 (2/17) — 메모리 상세 완성 + 환영 배너

| 순서 | 작업 | 담당 | 예상 | 선행 | 상세 |
|------|------|------|------|------|------|
| **11** | 메모리 상세 모달 완성 | FE | 4h | #10 | 삭제 버튼 + confirm 다이얼로그. `DELETE /api/v1/memories/{id}` 연결 (API 이미 존재). 관련 메모리 표시 (`/search/related/{id}` 활용) |
| **12** | 첫 방문 환영 배너 (P0-8) | FE | 4h | #4 | 메모리 0개 시 ChatView에 환영 카드. "메모리 추가하기" CTA → `/memories`. `localStorage` dismissed 플래그 |

**Day 5 체크포인트:**
- [x] 메모리 카드 클릭 → 상세 모달 열림
- [x] 상세 모달에서 삭제 가능
- [x] 신규 사용자에게 환영 배너 표시

### Day 6-7 (2/18-19) — 통합 QA

| 순서 | 작업 | 담당 | 예상 | 선행 | 상세 |
|------|------|------|------|------|------|
| **13** | 통합 QA | ALL | 2d | 전체 | 아래 체크리스트 참조 |

**통합 QA 체크리스트:**
- [ ] 토스트: 모든 API 에러에서 토스트 표시 확인
- [ ] 토스트: 메모리 추가 성공 토스트 확인
- [ ] 토스트: 3초 후 자동 소멸 + 수동 닫기
- [ ] 메모리 상세: 카드 클릭 → 모달 열림 → 정보 표시
- [ ] 메모리 삭제: confirm → API 호출 → 목록 갱신
- [ ] 새 대화: 버튼 클릭 → 새 세션 생성 → 메시지 입력 가능
- [ ] textarea: 여러 줄 입력 시 자동 확장, 200px에서 스크롤
- [ ] Escape: 모든 모달에서 Escape 닫기 동작
- [ ] 환영 배너: 메모리 0개 시 표시, dismiss 후 재표시 안 됨
- [ ] alert(): 전체 코드에서 alert() 0건
- [ ] 보안: 벡터 검색에서 다른 사용자 메모리 미노출 확인
- [ ] SSE: 채팅 스트리밍 정상 동작

---

## 5. 스프린트 2 상세 계획 (P1: 2026-02-19 ~ 2026-03-05)

### Week 2 전반 (2/19-2/21) — 디자인 정합성

| # | 작업 | 담당 | 예상 | 선행 | 상세 |
|---|------|------|------|------|------|
| P1-1 | glass-card 전면 교체 | FE | 1d | 없음 | MemoryView 5곳의 `glass-card` → `card` 교체. index.css의 `.glass-card` 규칙은 이미 평평한 카드로 변환됨 (실질적으로 클래스명 정리) |
| P1-2 | 네비게이션/UI 한국어화 | FE | 0.5d | 없음 | Sidebar: Chat→대화, Memories→기억, Journal→저널, Graph→그래프, Settings→설정. GraphView "Knowledge Graph is empty"→한국어. EditorToolbar 모드명 한국어화 |
| P1-9 | CSS 변수 잔존분 교체 | FE | 1d | 없음 | GraphView.css: `#0a0a0f` 하드코딩 제거, `backdrop-filter: blur()` 4곳 제거, `rgba()` 하드코딩 → CSS 변수. MemoryView.css: 그래디언트 하드코딩 교체 |

### Week 2 중반 (2/21-2/24) — 저널 AI 강화 + BE 작업

| # | 작업 | 담당 | 예상 | 선행 | 상세 |
|---|------|------|------|------|------|
| P1-13 | 저널 AI 강화 | 풀스택 | 2d | P1-1~3 | **핵심:** 기존 API 적극 활용 + UX 개선. (1) JournalView 진입 시 자동 회고 질문 표시 (기존 `review-questions` API), (2) 회고 템플릿 선택 UI ("오늘의 TIL", "이번 주 회고"), (3) 다이제스트 기반 토픽 추출 강화, (4) 빈 에디터 상태에서 "AI에게 질문받기" CTA |
| P1-4 | 채팅 세션 제목 자동 생성 | BE+FE | 1.5d | 없음 | BE: 첫 메시지 후 LLM으로 제목 생성, `PATCH /chat/sessions/{id}` 추가. FE: Sidebar 세션 목록에 제목 반영 |

### Week 2 후반 (2/24-2/26) — 접근성 + 기능

| # | 작업 | 담당 | 예상 | 선행 | 상세 |
|---|------|------|------|------|------|
| P1-3 | 모달 focus trap + ARIA | FE | 1d | P0-7 | `useFocusTrap` 커스텀 훅. 모든 모달에 `role="dialog"`, `aria-modal="true"`. 배경 스크롤 방지 |
| P1-5 | 저널 자동 저장 | FE | 1d | 없음 | 디바운스 2초로 `localStorage` 저장. 페이지 진입 시 복원 토스트. 서버 저장 성공 시 로컬 삭제 |
| P1-10 | 사용자 메시지 버블색 | FE | 0.5d | 없음 | 사용자 메시지에 `var(--accent-bg)` 배경 추가 |

### Week 3 전반 (2/26-2/28) — 반응형

| # | 작업 | 담당 | 예상 | 선행 | 상세 |
|---|------|------|------|------|------|
| P1-6 | 반응형 사이드바 | FE | 1.5d | 없음 | 768-1023px: 아이콘 전용 56px. <768px: 숨김 + 햄버거. `matchMedia` 연동 |
| P1-7 | JournalView 반응형 | FE | 1d | P1-6 | 1024px 이하: MemorySidebar → 에디터 하단 스택. collapsible 패널 |
| P1-8 | ARIA live region | FE | 0.5d | 없음 | ChatView 메시지 영역에 `aria-live="polite"` |

### Week 3 후반 (2/28-3/05) — AI 자동 판단 + 테마

| # | 작업 | 담당 | 예상 | 선행 | 상세 |
|---|------|------|------|------|------|
| P1-11 | Chat 모드 드롭다운 제거 + AI 자동 판단 | 풀스택 | 2d | 없음 | FE: 모드 드롭다운 UI 제거. BE: Socrates 에이전트에 의도 분류 로직 — 사용자 메시지 분석 후 메모리 검색 필요 여부 자동 판단. LangGraph 라우팅 노드 수정 |
| P1-12 | 시스템 테마 자동 전환 | FE | 0.5d | 없음 | `prefers-color-scheme` + SettingsView에 수동 토글(시스템/라이트/다크 3택) |

### 스프린트 2 진행 체크리스트

- [x] P1-1: glass-card 전면 교체 (`c1a2b3d`)
- [x] P1-2: 네비게이션/UI 한국어화 (`c1a2b3d`)
- [x] P1-9: CSS 변수 잔존분 교체 (`31459d9`)
- [x] P1-13: 저널 AI 강화 - 시작 도우미 + 템플릿 + 회고 질문 자동 생성 (`aae612b`)
- [x] P1-4: 채팅 세션 제목 자동 생성 (`d358814`)
- [x] P1-3: 모달 focus trap + ARIA 접근성 (`51db789`)
- [x] P1-5: 저널 자동 저장 - localStorage 디바운스 저장/복원 (`fb49960`)
- [x] P1-10: 사용자 메시지 버블색 — 이미 구현 확인 (CSS에 `var(--accent-primary)` 적용됨)
- [x] P1-6: 반응형 사이드바 - 태블릿 아이콘 전용 + 모바일 슬라이드인 (`e87bcf9`)
- [x] P1-8: ARIA live region - ChatView aria-live="polite" (`e87bcf9`)
- [x] P1-7: JournalView 반응형 - ≤1024px 세로 스택 + 사이드바 접기/펼치기 (`200c695`)
- [x] P1-11: Chat 모드 드롭다운 제거 + AI 자동 의도 분류 (`084d8a1`)
- [x] P1-12: 시스템 테마 자동 전환 + 수동 3택 토글 (`316a177`)

---

## 5.5. 스프린트 3 상세 계획 (P2 Phase 1: 2026-03-05 ~ 2026-03-19)

**목표:** "주변 지인이 사용할 수 있는" 상태 — 저널 히스토리, GraphView 강화, 글로벌 검색

### Day 1 — GraphView 한국어화

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| P2-4 | GraphView 전면 한국어화 | FE | 1d | 노드 타입 라벨(Memory→메모리, Entity→엔티티 등) 한국어 매핑, 범례 라벨, 정보 패널 관계 타입 한국어화, 잔존 영문 텍스트 정리 |

### Day 2-4 — 저널 히스토리

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| P2-1 | 저널 히스토리 (과거 저널 조회) | 풀스택 | 3d | BE: `GET /api/journal/history` (날짜별 목록), 날짜 기반 저널 조회. FE: JournalView에 날짜 선택 UI, 과거 저널 읽기 모드 |

### Day 5-6 — 글로벌 검색

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| P2-3 | 글로벌 검색 (Cmd+K) | FE | 2d | 키보드 단축키로 검색 팔레트 열림. 메모리, 채팅 세션, 저널 통합 검색. 기존 벡터 검색 API 재활용 |

### Day 7 — KuzuDB 영속성

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| P2-8 | KuzuDB 영속성 확인 | 인프라 | 1d | Fly.io 볼륨 마운트 설정 확인, 컨테이너 재시작 시 그래프 데이터 유실 테스트 |

### Day 8-10 — GraphView 상호작용 강화

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| P2-11 | GraphView 상호작용 강화 | FE | 3d | 노드 클릭→메모리 상세 연결, 클러스터 탐색 UI, 시간 흐름 필터, 검색 결과 하이라이트 |

### 스프린트 3 진행 체크리스트

- [x] P2-4: GraphView 전면 한국어화 (`8d4bafb`)
- [x] P2-1: 저널 히스토리 - 과거 저널 조회 + 날짜 네비게이션 (`59e4142`)
- [x] P2-3: 글로벌 검색 Ctrl+K 커맨드 팔레트 (`200c933`)
- [x] P2-8: KuzuDB 영속성 - Fly.io 볼륨 경로 연결 (`0efbf8e`)
- [x] P2-11: GraphView 상호작용 강화 (`48d89a5`)

---

## 5.6. 스프린트 4 상세 계획 (P2 Phase 2)

**목표:** 리텐션 + 접근성 + 모바일 완성 — 사용자 유지율 기반 확보

### Day 1-3 — 리텐션 대시보드

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| P2-2 | 리텐션 대시보드 (스트릭, 추세) | 풀스택 | 3d | 저널 작성 스트릭, 주간 메모리 추세, 주제 변화 시각화. 연속 기록 축하 메시지 |

### Day 4-6 — 모바일 반응형 완성

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| P2-5 | 모바일 반응형 완성 | FE | 3d | 모든 뷰의 모바일 레이아웃 최적화. 터치 인터랙션 고려 |

### Day 7-8 — 키보드 접근성

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| P2-6 | 키보드 접근성 강화 | FE | 2d | 전체 탭 순서 구현, 커스텀 컴포넌트 키보드 네비게이션 |

### Day 9-10 — 다이제스트 스케줄러

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| P2-7 | 다이제스트 봇 스케줄러 | BE | 2d | 매일 저녁 자동 다이제스트 생성. APScheduler 기반 |

### 스프린트 4 진행 체크리스트

- [x] P2-2: 리텐션 대시보드 - 스트릭, 통계, 활동 히트맵, 태그 분석 (`2913066`)
- [x] P2-5: 모바일 반응형 완성 - 8개 뷰 미디어 쿼리 추가 (`36db819`)
- [x] P2-6: 키보드 접근성 강화 - 시맨틱 버튼, ARIA, 스킵 링크 (`65932de`)
- [x] P2-7: 다이제스트 봇 스케줄러 - APScheduler 크론 + 수동 트리거 (`cf7f728`)

---

## 6. 파일별 수정 매핑

### 6.1 스프린트 1 터치 파일

```
신규 생성:
  frontend/src/contexts/ToastContext.tsx          ← P0-1: 글로벌 토스트
  frontend/src/components/MemoryDetailModal.tsx   ← P0-4: 메모리 상세 모달
  frontend/src/components/WelcomeBanner.tsx       ← P0-8: 환영 배너

수정:
  backend/app/agents/socrates/nodes/chat.py       ← P0-9: user_id 필터 (2곳)
  frontend/src/App.tsx                            ← P0-1: ToastProvider 래핑
  frontend/src/components/ChatView.tsx            ← P0-2: catch 토스트, P0-5: auto-resize, P0-8: 배너
  frontend/src/components/MemoryView.tsx          ← P0-2: catch 토스트, P0-3: 성공 피드백, P0-4: 클릭 핸들러
  frontend/src/components/JournalView.tsx         ← P0-2: catch 토스트, 로컬 토스트 마이그레이션
  frontend/src/components/Sidebar.tsx             ← P0-6: 새 대화 버튼
  frontend/src/components/journal/AIPanel.tsx     ← P0-4: alert → 토스트
  frontend/src/components/journal/AIBubbleMenu.tsx ← P0-4: alert → 토스트
  frontend/src/components/journal/SessionPickerModal.tsx ← P0-7: Escape
  frontend/src/components/SettingsView.tsx        ← 로컬 토스트 → 글로벌 마이그레이션
  frontend/src/Sidebar.css                        ← P0-6: 새 대화 버튼 스타일
```

### 6.2 스프린트 2 터치 파일

```
신규 생성:
  frontend/src/hooks/useFocusTrap.ts              ← P1-3: focus trap 훅

수정:
  backend/app/agents/socrates/nodes/chat.py       ← P1-11: 의도 분류 로직
  backend/app/routers/chat_router.py              ← P1-4: 세션 제목 PATCH
  backend/app/services/chat_service.py            ← P1-4: 제목 생성 로직
  frontend/src/components/MemoryView.tsx          ← P1-1: glass-card 교체
  frontend/src/components/ChatView.tsx            ← P1-8: aria-live, P1-10: 버블색, P1-11: 드롭다운 제거
  frontend/src/components/Sidebar.tsx             ← P1-2: 한국어화, P1-6: 반응형
  frontend/src/components/JournalView.tsx         ← P1-5: 자동저장, P1-7: 반응형, P1-13: AI 강화
  frontend/src/components/GraphView.tsx           ← P1-2: 한국어화
  frontend/src/components/journal/EditorToolbar.tsx ← P1-2: 모드명 한국어화
  frontend/src/components/journal/AIPanel.tsx     ← P1-13: 회고 질문 자동 표시
  frontend/src/components/journal/MemorySidebar.tsx ← P1-13: 토픽 추출 강화
  frontend/src/GraphView.css                      ← P1-9: 하드코딩 제거, glassmorphism 제거
  frontend/src/MemoryView.css                     ← P1-9: 그래디언트 교체
  frontend/src/Sidebar.css                        ← P1-6: 반응형 미디어 쿼리
  frontend/src/JournalView.css                    ← P1-7: 반응형 스택
  frontend/src/ChatView.css                       ← P1-10: 메시지 버블색
  frontend/src/index.css                          ← P1-12: 테마 토글 변수
  frontend/src/components/SettingsView.tsx        ← P1-12: 테마 3택 UI
```

---

## 7. 의존성 그래프 (작업 순서 제약)

```
=== 스프린트 1 (P0) ===

P0-9 (보안) ─────────────────────────────────── 독립, 최우선
P0-5 (auto-resize) ─────────────────────────── 독립
P0-7 (Escape) ──────────────────────────────── 독립
P0-6 (새 대화) ─────────────────────────────── 독립

P0-1 (토스트) ──┬──> P0-2 (catch 연결)
               ├──> P0-3 (성공 피드백)
               ├──> P0-4 (alert 교체)
               └──> P0-8 (환영 배너, 토스트 활용)

P0-4 (메모리 상세 모달) ─────────────────────── 독립 (DELETE API 이미 존재)

=== 스프린트 2 (P1) ===

P1-1 (glass-card) ──┐
P1-2 (한국어화) ────┼──> P1-13 (저널 AI 강화)
P1-9 (CSS 정리) ────┘

P0-7 (Escape) ──────────> P1-3 (focus trap + ARIA)

P1-6 (반응형 사이드바) ──> P1-7 (JournalView 반응형)

P1-4 (세션 제목) ────────────────────────────── 독립
P1-5 (자동저장) ─────────────────────────────── 독립
P1-11 (AI 자동판단) ─────────────────────────── 독립
P1-12 (테마 전환) ───────────────────────────── 독립
```

---

## 8. 리스크 및 대응

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| 토스트 시스템이 기존 로컬 토스트와 충돌 | P0 전체 지연 | 중 | JournalView/SettingsView 로컬 토스트를 글로벌로 마이그레이션하면서 기존 스타일 유지 |
| 메모리 상세 모달에서 관련 메모리 API 느림 | UX 저하 | 중 | 모달 열림 시 기본 정보 먼저 표시, 관련 메모리는 비동기 로딩 (로딩 스피너) |
| Socrates 의도 분류(P1-11) 정확도 부족 | Chat UX 저하 | 높 | 우선 간단한 키워드 기반 분류로 시작. "내 메모리", "저장한", "읽었던" 등 명시적 키워드 감지 → 벡터 검색. 나머지 → 일반 대화 |
| 반응형 사이드바(P1-6)가 세션 목록 UI 깨뜨림 | Sidebar 기능 저하 | 중 | 아이콘 모드에서는 세션 목록 숨김. 확장 시에만 표시 |
| 무료 티어 LLM 호출 비용 증가 | 인프라 비용 | 낮 | 세션 제목 생성은 gpt-4o-mini 사용 (비용 최소). 저널 AI도 기존 API 재활용 |

---

## 9. 성공 메트릭 (dogfooding 기준)

### 스프린트 1 완료 기준 (Phase 1)

| 메트릭 | 기준 | 검증 방법 |
|--------|------|----------|
| 핵심 플로우 막힘 | 0건 | 파운더가 수집→대화→회고 플로우를 처음부터 끝까지 수행 |
| 크리티컬 버그 | 0건 | 벡터 검색 보안, SSE 스트리밍 정상 동작 |
| alert() 잔존 | 0건 | `grep -r "alert(" frontend/src/` 결과 0건 |
| 사용자 피드백 | 모든 액션 | 성공/실패 시 토스트 표시 확인 |

### 스프린트 2 완료 기준 (Phase 2 시작)

| 메트릭 | 기준 | 검증 방법 |
|--------|------|----------|
| 파운더 일일 사용 | 주 5일 | 실제 사용 로그 |
| 저널 작성 빈도 | 주 3회 이상 | 저널 API 호출 로그 |
| UI 언어 일관성 | 한국어 100% | 전체 UI 수동 점검 (제품명/OAuth 제외) |
| 반응형 | 768px 이상 정상 | 태블릿 시뮬레이션 점검 |

---

## 10. 커밋 컨벤션

```
feat: 글로벌 토스트 시스템 구축 (P0-1)
fix: Socrates 벡터 검색 user_id 필터 누락 수정 (P0-9)
feat: 메모리 상세 모달 구현 (P0-4)
style: glass-card 전면 교체 (P1-1)
feat: 네비게이션 한국어화 (P1-2)
refactor: Chat 모드 드롭다운 제거 + AI 자동 판단 (P1-11)
```

태그 규칙:
- `feat`: 새 기능
- `fix`: 버그 수정 (보안 포함)
- `style`: 스타일/디자인 변경
- `refactor`: 기능 변경 없는 코드 개선
- 커밋 메시지는 한국어, 본문에 P0/P1 번호 명시

---

## 11. 스프린트 4 회고 (Retrospective)

**기간:** Sprint 4 (P2 Phase 2)
**회고일:** 2026-02-13
**완료 항목:** P2-2, P2-5, P2-6, P2-7 (4/4 = 100% 완료)

### 11.1 Sprint 4 완료 사항 점검

| # | 작업 | 커밋 | 산출물 요약 | 품질 평가 |
|---|------|------|-----------|----------|
| P2-2 | 리텐션 대시보드 | `2913066` | BE: /stats/streak, /stats/overview, /stats/activity 3개 엔드포인트 신규. FE: DashboardView 컴포넌트(스트릭 카드+통계 그리드+60일 히트맵+태그 바 차트). Sidebar 네비게이션 연동. | **12파일, +513줄**. 풀스택 완성도 높음. 스트릭 계산 로직(현재/최장/총 활동일) 견고. 축하 메시지 7단계 세분화. |
| P2-5 | 모바일 반응형 완성 | `36db819` | 8개 CSS 파일에 767px 브레이크포인트 미디어 쿼리 일괄 추가. ChatView/CommandPalette/AuthView/MemoryView/JournalView/DashboardView/GraphView/SettingsView 대응. | **8파일, +159줄**. 전체 뷰 커버리지 달성. 햄버거 메뉴 여백(padding-left) 일관 처리. |
| P2-6 | 키보드 접근성 강화 | `65932de` | MemoryView/GraphView에서 div->button 시맨틱 전환. aria-label, aria-pressed, aria-expanded 추가. AppLayout에 스킵 네비게이션 링크. ToastContext에 aria-live/role 추가. | **8파일, +59줄**. 웹 접근성 기초 확립. WCAG 2.1 AA 수준 접근. |
| P2-7 | 다이제스트 봇 스케줄러 | `cf7f728` | APScheduler AsyncIOScheduler로 매 정시 크론 작업. 사용자별 delivery_hour 기반 다이제스트 생성. kakao_delivery_log 기록. FastAPI lifespan으로 스케줄러 생명주기 관리. 수동 트리거 엔드포인트. | **4파일, +146줄**. 에러 핸들링 견고(per-user try/catch, 전송 실패 기록). |

### 11.2 잘한 점 (Keep)

1. **풀스택 일관성**: P2-2(리텐션 대시보드)는 BE 스키마/리포지토리/서비스/라우터 4계층과 FE 타입/API/컴포넌트/CSS를 한 커밋에 완결. 의존성 없이 독립 배포 가능한 구조.

2. **전체 뷰 커버리지**: P2-5에서 8개 뷰를 빠짐없이 반응형 처리. 767px 브레이크포인트 통일로 일관된 모바일 경험.

3. **접근성 기초 확립**: P2-6에서 시맨틱 HTML 전환(div->button)을 통해 키보드 사용자가 Tab+Enter로 핵심 기능에 접근 가능. 스킵 네비게이션 링크는 스크린 리더 사용자 대비.

4. **인프라 자동화 기반**: P2-7의 APScheduler + FastAPI lifespan 패턴은 향후 넛지 시스템(P2-10)의 기반 인프라로 재활용 가능.

5. **커밋 품질**: 4개 커밋 모두 한국어 커밋 메시지 컨벤션 준수. 본문에 변경 사항 구체적 나열. P2 번호 명시.

### 11.3 개선점 (Improve)

1. **DashboardView에 토스트 미연결**: DashboardView.tsx:45에서 `console.error('대시보드 데이터 로딩 실패:', err)` 만 있고 `useToast()` 미사용. Sprint 1에서 확립한 글로벌 토스트 패턴이 신규 컴포넌트에 전파되지 않음. GraphView도 동일 문제(120행).

2. **히트맵 색상 하드코딩**: DashboardView.tsx:23에서 `rgba(139, 92, 246, ${alpha})` 인라인 하드코딩. CSS 변수 `var(--accent-primary)` 활용이 바람직. Sprint 2(P1-9)에서 하드코딩 제거를 했으나 신규 코드에 재발.

3. **스케줄러 실제 전송 미완**: scheduler_service.py:87에 `# TODO: 카카오 메시지 API로 실제 전송` 주석 존재. 다이제스트 "생성"까지만 완료, 실제 "전송"은 미구현. P2-10(넛지 시스템)에서 해결 필요.

4. **모바일 터치 최적화 부족**: P2-5에서 레이아웃 반응형은 완료했으나, 터치 타겟 사이즈(최소 44x44px), 스와이프 제스처, 터치 피드백(active state) 등은 미처리.

### 11.4 Sprint 4 종합 평가

Sprint 4는 **"사용자 유지율 기반 확보"** 목표에 부합하는 결과물을 산출했다. 특히 리텐션 대시보드와 스케줄러는 향후 넛지 시스템의 핵심 인프라가 된다. 모바일 반응형과 접근성은 외부 사용자 확장의 전제 조건이었으며, 이를 달성함으로써 Phase 3("외부 유저 확보") 진입 준비를 마쳤다.

---

## 12. P0~P2(Phase 1+2) 완료 후 전체 제품 상태 평가

### 12.1 종합 점수표 (업데이트)

| 평가 항목 | Sprint 1 시작 | Sprint 4 완료 후 | 변화 |
|-----------|:----------:|:------------:|:----:|
| 기능 범위 (Feature Scope) | 7.4/10 | **9.0/10** | +1.6 |
| 기능 깊이 (Feature Depth) | 5.4/10 | **7.5/10** | +2.1 |
| UX 완성도 | 4.3/10 | **7.0/10** | +2.7 |
| 코드 품질 | 7.5/10 | **8.0/10** | +0.5 |
| PMF 준비도 | 3.3/10 | **6.5/10** | +3.2 |

### 12.2 달성한 것

**Phase 1 목표 ("파운더가 매일 사용할 수 있는 상태")**: 달성.
- 핵심 플로우(수집 -> 대화 -> 회고) 막힘 0건
- 글로벌 토스트로 모든 액션에 피드백 제공
- 메모리 상세 모달, 새 대화 버튼, 저널 자동저장 등 일상 사용 기반 완비

**Phase 2 목표 ("주변 지인이 사용할 수 있는 상태")**: 대부분 달성.
- 한국어 UI 100% 통일 (제품명/OAuth 제외)
- 반응형 레이아웃 완성 (데스크톱/태블릿/모바일)
- 접근성 기초 (ARIA, 키보드, 스킵 링크)
- 저널 히스토리, GraphView 상호작용, 글로벌 검색, 리텐션 대시보드

### 12.3 아키텍처 현황 (Sprint 4 완료 기준)

```
프론트엔드: React 18 + TypeScript + Vite
  - 7개 주요 뷰: ChatView, MemoryView, JournalView, GraphView, DashboardView, SettingsView, AuthView
  - 글로벌 인프라: ToastContext, ThemeContext, AuthContext, CommandPalette
  - 반응형: 767px/1024px 브레이크포인트 전체 적용
  - 접근성: ARIA 라벨, 시맨틱 HTML, 스킵 네비게이션, focus trap

백엔드: FastAPI + Python
  - 9개 라우터: memory, chat, graph, search, auth, integrations, stats, journal, digest
  - 에이전트: Socrates (대화 + 자동 의도 분류), Librarian (메모리 처리)
  - 인프라: APScheduler (다이제스트 크론), Supabase (PostgreSQL + pgvector), KuzuDB (그래프)
  - SSE 스트리밍, JWT 인증, user_id 필터 보안

Chrome Extension: v1.1
  - Google OAuth, 원클릭 페이지 저장, Fly.io 백엔드 연동
```

### 12.4 남은 기술 부채

| # | 항목 | 심각도 | 위치 |
|---|------|--------|------|
| TD-1 | DashboardView/GraphView에 토스트 미연결 | 중 | DashboardView.tsx:45, GraphView.tsx:120 |
| TD-2 | DashboardView 히트맵 색상 하드코딩 | 낮 | DashboardView.tsx:23, :134 |
| TD-3 | 스케줄러 카카오 실제 전송 미완 | 중 | scheduler_service.py:87 TODO |
| TD-4 | 모바일 터치 타겟 사이즈 미검증 | 낮 | 전체 컴포넌트 |
| TD-5 | Chrome Extension 다크모드 고정 | 낮 | popup.html 인라인 스타일 |

---

## 13. 스프린트 5 상세 계획 (P2 Phase 3: Chrome Extension + 넛지 시스템)

**목표:** "외부 유저 확보 준비" — 수집 허들 최소화 + 능동적 참여 유도 시스템 구축
**기간:** 약 10일 (8 작업일 + 2일 QA)
**선행 조건:** Sprint 4 완료 (P2-7 스케줄러 인프라 활용)

### 전략적 배경

Sprint 1~4를 통해 핵심 제품 루프(수집 -> 정리 -> 대화 -> 회고)가 완성되었고, 리텐션 인프라(대시보드, 스케줄러)도 갖추었다. Sprint 5는 이 루프의 **양 끝단**을 강화한다:

1. **입구 강화 (P2-9 Chrome Extension)**: 수집 마찰을 최소화하여 더 많은 기억이 유입되도록
2. **출구 강화 (P2-10 넛지 시스템)**: 수동적 도구에서 능동적 파트너로 전환하여 사용자를 다시 데려오도록

두 작업은 독립적이므로 병렬 진행 가능하다. P2-9를 먼저 완료하여 빠른 성과를 내고, P2-10을 후반부에 배치한다.

```
┌─────────────────────────────────────────────────────────────────┐
│                    스프린트 5 (P2 Phase 3)                        │
│                                                                 │
│  Track A (Extension)      Track B (넛지 시스템)                  │
│  ─────────────────────    ────────────────────────────           │
│  Day 1:                   Day 1:                                │
│  기술 부채 정리 (TD-1~5)   넛지 DB 스키마 + 알림 설정 API         │
│                                                                 │
│  Day 2-3:                 Day 3-4:                              │
│  Extension 리팩토링        브라우저 푸시 알림 인프라                │
│  + 페이지 본문 추출         + Service Worker                      │
│  + 태그 입력 UI                                                  │
│                           Day 5-6:                              │
│  Day 4:                   넛지 스케줄러 로직 구현                  │
│  Extension 컨텍스트 메뉴    + 3종 넛지 생성 (저녁 회고/주간/연결)   │
│  + 텍스트 선택 저장                                               │
│                           Day 7:                                │
│  Day 5:                   알림 설정 UI (SettingsView)             │
│  Extension QA + 배포                                             │
│                                                                 │
│  Day 8-10: 통합 QA + 기술 부채 잔여분                             │
└─────────────────────────────────────────────────────────────────┘
```

---

### Day 1 — 기술 부채 정리 + 넛지 DB 설계

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| S5-0a | 기술 부채 정리 (TD-1~5) | FE | 0.5d | DashboardView/GraphView에 `useToast()` 연결. 히트맵 색상을 CSS 변수로 교체. Extension popup.html에 다크/라이트 모드 지원. |
| S5-0b | 넛지 시스템 DB 스키마 설계 | BE | 0.5d | Supabase에 `notification_settings` 테이블 생성: user_id, channel(push/email), nudge_type(evening_review/weekly_summary/connection_found), enabled, delivery_hour, timezone. `notification_log` 테이블: id, user_id, nudge_type, content, status(sent/read/clicked), sent_at. |

**Day 1 체크포인트:**
- [ ] DashboardView/GraphView 에러 시 토스트 표시 확인
- [ ] 히트맵 색상에 CSS 변수 적용 확인
- [ ] notification_settings / notification_log 테이블 마이그레이션 완료
- [ ] `GET/PATCH /api/v1/settings/notifications` API 동작 확인

---

### Day 2-3 — Chrome Extension 핵심 개선 (P2-9)

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| S5-1 | Extension 코드 리팩토링 | FE | 0.5d | popup.js를 모듈화(auth.js, api.js, ui.js). 하드코딩 API URL을 환경 설정으로 분리. 에러 핸들링 강화(네트워크 오류, 토큰 만료 시 자동 갱신). |
| S5-2 | 페이지 본문 자동 추출 | FE | 1d | content_script.js 신규: `document.body.innerText` 또는 Readability.js 기반으로 페이지 핵심 본문 추출. popup에서 "본문 포함" 토글 추가. 저장 시 `content` 필드로 백엔드 전송. 백엔드: 기존 `/memories` POST에 `content` 선택 필드 추가(이미 존재할 수 있음 확인). |
| S5-3 | 사용자 메모/태그 입력 UI | FE | 0.5d | popup.html에 textarea(메모 입력, 3줄)와 태그 입력 칩(comma-separated). 저장 시 `memo`와 `tags` 필드로 전송. |
| S5-4 | 저장 완료 후 피드백 개선 | FE | 0.3d | 저장 성공 시 체크 아이콘 애니메이션 + 3초 후 자동 닫기. 저장 이력 배지(오늘 N개 저장). |

**Day 2-3 체크포인트:**
- [ ] popup.js 모듈 분리 완료
- [ ] 아무 웹 페이지에서 저장 시 본문 내용이 메모리에 포함되는지 확인
- [ ] 메모/태그 입력 후 저장 시 백엔드에 반영되는지 확인
- [ ] 토큰 만료 시 자동 재로그인 플로우 동작 확인

---

### Day 3-4 — 브라우저 푸시 알림 인프라 (P2-10 전반)

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| S5-5 | 알림 설정 API | BE | 0.5d | `GET /api/v1/settings/notifications` — 사용자 알림 설정 조회. `PATCH /api/v1/settings/notifications` — 알림 설정 변경. 기본값: evening_review=true(21시), weekly_summary=true(일요일), connection_found=true. |
| S5-6 | Web Push 인프라 (Service Worker) | FE+BE | 1.5d | FE: Service Worker 등록, Push API 구독, 알림 수신 시 Notification 표시. 알림 클릭 시 해당 페이지로 이동(저널/대시보드). BE: web-push 라이브러리(pywebpush) 설치. push_subscription 테이블(user_id, endpoint, p256dh, auth). VAPID 키 생성 및 환경변수 등록. `POST /api/v1/push/subscribe` 구독 등록. |

**Day 3-4 체크포인트:**
- [ ] Service Worker 등록 및 Push 구독 정상 동작
- [ ] 테스트 푸시 알림 수신 확인 (브라우저 알림 팝업)
- [ ] 알림 클릭 시 앱 내 해당 페이지로 이동

---

### Day 4 — Chrome Extension 컨텍스트 메뉴 (P2-9 후반)

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| S5-7 | 컨텍스트 메뉴(우클릭) 저장 | FE | 0.5d | background.js(Service Worker) 신규: `chrome.contextMenus.create({ title: "Memoir에 저장" })`. 텍스트 선택 후 우클릭 시 선택한 텍스트 + 페이지 URL을 메모리로 저장. 키보드 단축키 등록: `Ctrl+Shift+M` → 현재 페이지 즉시 저장 (manifest commands). |
| S5-8 | Extension 다크/라이트 테마 | FE | 0.3d | `prefers-color-scheme` 미디어 쿼리로 popup.html 스타일 분기. 라이트 모드: 밝은 배경 + 어두운 텍스트. |

**Day 4 체크포인트:**
- [ ] 텍스트 선택 → 우클릭 → "Memoir에 저장" → 선택 텍스트가 메모리로 저장
- [ ] Ctrl+Shift+M 단축키로 현재 페이지 즉시 저장
- [ ] OS 라이트 모드에서 Extension 팝업이 밝은 테마로 표시

---

### Day 5-6 — 넛지 스케줄러 로직 구현 (P2-10 핵심)

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| S5-9 | 저녁 회고 넛지 생성 | BE | 0.5d | 기존 `scheduler_service.py`에 `evening_review_job()` 추가. 매일 사용자별 delivery_hour에 실행. 오늘 수집된 메모리 수 + 주요 토픽 요약 → 푸시 알림 메시지 생성: "오늘 {N}개의 새 기억이 쌓였습니다. {토픽1}, {토픽2} 주제로 저널을 써볼까요?" notification_log에 기록. |
| S5-10 | 주간 요약 넛지 생성 | BE | 0.5d | `weekly_summary_job()` 추가. 매주 일요일 실행. 이번 주 메모리/저널/대화 통계 + 가장 많이 다룬 주제 + 스트릭 현황 → 푸시 알림. StatsService.get_overview() 재활용. |
| S5-11 | 연결 발견 넛지 | BE | 1d | `connection_discovery_job()` 추가. 새 메모리 저장 시 (또는 일일 배치로) 기존 메모리와의 유사도 검사. 유사도 높은 쌍 발견 시 → "최근 저장한 '{제목A}'가 2주 전 '{제목B}'와 연결됩니다" 알림. 벡터 검색 기반: 새 메모리의 임베딩으로 기존 메모리 검색, 유사도 threshold(0.85) 이상 + 시간 간격 3일 이상인 쌍. |
| S5-12 | 넛지 전송 엔진 통합 | BE | 0.5d | `send_nudge()` 공통 함수: notification_settings 확인 → 채널별 분기(push/email). Web Push: pywebpush로 구독 엔드포인트에 전송. 이메일: 향후 확장 포인트(현재는 push only). notification_log에 전송 결과 기록. |

**Day 5-6 체크포인트:**
- [ ] 수동 트리거로 저녁 회고 넛지가 생성되고 푸시 알림 수신 확인
- [ ] 주간 요약 넛지 수동 트리거 시 통계 포함된 알림 수신 확인
- [ ] 새 메모리 저장 시 연결 발견 알림이 조건부로 발생하는지 확인
- [ ] notification_log에 전송 기록이 남는지 확인

---

### Day 5 — Chrome Extension QA + 배포

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| S5-13 | Extension 통합 QA | FE | 0.5d | 인증 플로우 (로그인/로그아웃/토큰 만료 갱신), 페이지 저장 (URL only/본문 포함/메모+태그), 컨텍스트 메뉴, 키보드 단축키, 다크/라이트 모드, 에러 시나리오(네트워크 끊김, 서버 다운). manifest.json 버전 1.1→1.2 업데이트. |

---

### Day 7 — 알림 설정 UI

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| S5-14 | SettingsView 알림 설정 UI | FE | 1d | SettingsView에 "알림 설정" 섹션 추가. 3종 넛지 개별 토글(저녁 회고/주간 요약/연결 발견). 저녁 회고 시간 선택 드롭다운(19시~23시). 브라우저 푸시 권한 요청 버튼("알림 허용"). 권한 상태 표시(허용됨/차단됨/미설정). `PATCH /api/v1/settings/notifications` 연동. |

**Day 7 체크포인트:**
- [ ] SettingsView에서 알림 토글 ON/OFF 시 서버에 반영
- [ ] 시간 변경 시 다음 넛지부터 새 시간에 발송
- [ ] 브라우저 알림 권한 요청 정상 동작
- [ ] 권한 차단 상태에서 적절한 안내 메시지 표시

---

### Day 8-10 — 통합 QA + 엣지 케이스

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| S5-15 | 통합 QA | ALL | 2d | 아래 체크리스트 참조 |
| S5-16 | 잔존 기술 부채 처리 | ALL | 1d | QA 과정에서 발견된 이슈 수정 |

**통합 QA 체크리스트:**

Chrome Extension:
- [ ] Google OAuth 로그인/로그아웃 정상 동작
- [ ] 토큰 만료 시 자동 갱신 (401 -> 재인증 플로우)
- [ ] 일반 페이지 저장: URL + 제목 전송 확인
- [ ] 본문 포함 저장: content 필드에 핵심 텍스트 포함 확인
- [ ] 메모 + 태그 입력 후 저장 시 백엔드 반영 확인
- [ ] 컨텍스트 메뉴: 텍스트 선택 → 우클릭 → 저장 확인
- [ ] 키보드 단축키: Ctrl+Shift+M → 즉시 저장
- [ ] 저장 성공 애니메이션 + 자동 닫기
- [ ] 다크/라이트 모드 전환 확인
- [ ] 에러 시나리오: 네트워크 끊김, 서버 500, 인증 만료

넛지 시스템:
- [ ] 저녁 회고 넛지: 설정 시간에 푸시 알림 수신
- [ ] 주간 요약 넛지: 일요일에 통계 포함 알림 수신
- [ ] 연결 발견 넛지: 유사 메모리 발견 시 알림 수신
- [ ] 알림 클릭 → 앱 내 해당 페이지로 이동
- [ ] 알림 설정 OFF 시 넛지 미발송 확인
- [ ] notification_log에 전송/읽기/클릭 상태 기록
- [ ] 활동 없는 날 넛지 미발송 (또는 "오늘은 쉬어가요" 메시지)

기존 기능 회귀:
- [ ] Chat SSE 스트리밍 정상 동작
- [ ] 메모리 CRUD + 검색 정상 동작
- [ ] 저널 작성/자동저장/히스토리 정상 동작
- [ ] 대시보드 스트릭/통계/히트맵 정상 표시
- [ ] 글로벌 검색 Ctrl+K 정상 동작
- [ ] GraphView 노드 클릭/검색 정상 동작

---

### 스프린트 5 파일별 수정 매핑

```
=== Chrome Extension (P2-9) ===

수정:
  extension/manifest.json                    ← v1.2 업데이트, commands, contextMenus 권한
  extension/popup.html                       ← 메모/태그 입력 UI, 다크/라이트 테마
  extension/popup.js                         ← 모듈화, 본문 추출 연동, 토큰 갱신

신규 생성:
  extension/content_script.js                ← 페이지 본문 추출 (Readability 기반)
  extension/background.js                    ← Service Worker, 컨텍스트 메뉴, 키보드 단축키
  extension/auth.js                          ← 인증 모듈 분리 (OAuth, 토큰 관리)
  extension/api.js                           ← API 호출 모듈 분리

=== 넛지 시스템 (P2-10) ===

백엔드 신규:
  backend/app/services/nudge_service.py      ← 3종 넛지 생성 로직
  backend/app/services/push_service.py       ← Web Push 전송 엔진 (pywebpush)
  backend/app/routers/push_router.py         ← POST /push/subscribe
  backend/app/routers/notification_router.py ← GET/PATCH /settings/notifications
  backend/app/repositories/notification_repository.py  ← notification_settings/log CRUD
  backend/app/schemas/notification_schema.py ← Pydantic 스키마

백엔드 수정:
  backend/app/services/scheduler_service.py  ← evening_review_job, weekly_summary_job, connection_discovery_job 추가
  backend/app/routers/router.py              ← push_router, notification_router 등록
  backend/app/config/settings.py             ← VAPID 키 환경변수
  backend/app/config/dependencies.py         ← nudge_service, push_service DI
  backend/requirements.txt                   ← pywebpush 추가

프론트엔드 수정:
  frontend/src/components/SettingsView.tsx    ← 알림 설정 섹션 추가
  frontend/src/components/SettingsView.css   ← 알림 설정 스타일
  frontend/src/api/notifications.ts          ← 알림 설정 API 클라이언트 (신규)
  frontend/public/sw.js                      ← Service Worker for Push (신규)
  frontend/src/App.tsx                       ← Service Worker 등록

=== 기술 부채 (TD-1~5) ===

수정:
  frontend/src/components/DashboardView.tsx  ← useToast() 연결 + 히트맵 CSS 변수화
  frontend/src/components/GraphView.tsx      ← useToast() 연결
```

---

### 스프린트 5 의존성 그래프

```
S5-0a (기술 부채) ─────────────────────── 독립, 최우선
S5-0b (넛지 DB) ───────────────────────── 독립, 최우선

S5-1 (Extension 리팩) ──┬──> S5-2 (본문 추출)
                        ├──> S5-3 (메모/태그 UI)
                        ├──> S5-7 (컨텍스트 메뉴)
                        └──> S5-8 (Extension 테마)

S5-2 + S5-3 + S5-4 ────────> S5-13 (Extension QA)
S5-7 + S5-8 ───────────────> S5-13

S5-0b (넛지 DB) ──> S5-5 (알림 설정 API) ──> S5-14 (알림 설정 UI)

S5-6 (Push 인프라) ──> S5-12 (넛지 전송 엔진)

S5-5 + S5-6 ──> S5-9 (저녁 회고)
              ──> S5-10 (주간 요약)
              ──> S5-11 (연결 발견)

S5-9 + S5-10 + S5-11 + S5-12 ──> S5-14 (알림 설정 UI)

전체 ──> S5-15 (통합 QA) ──> S5-16 (잔존 이슈)
```

---

### 스프린트 5 리스크 및 대응

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| Web Push 브라우저 권한 거부율 높음 | 넛지 도달률 저하 | 높 | 첫 저널 작성 완료 시점에 권한 요청(성취감 순간). 권한 거부 시 앱 내 인앱 알림으로 대체(DashboardView 배너). |
| Chrome Extension content_script가 특정 사이트에서 실패 | 수집 실패 | 중 | try-catch로 감싸고, 본문 추출 실패 시 URL+제목만 저장(graceful degradation). CSP 제한 사이트(은행 등) 대비. |
| 연결 발견 넛지의 오탐(false positive) | 사용자 피로 | 중 | 유사도 threshold를 보수적으로 설정(0.85 이상). 하루 최대 1건 제한. "이 알림이 유용했나요?" 피드백 버튼. |
| pywebpush + VAPID 키 설정 복잡도 | 개발 지연 | 중 | VAPID 키 생성 스크립트 준비. Fly.io 환경변수로 주입. 로컬 개발 시 mock push service 사용. |
| 스케줄러 크론 작업 중복 실행 (Fly.io 복수 인스턴스) | 알림 중복 | 낮 | Fly.io 무료 티어는 단일 인스턴스. 향후 스케일 시 분산 락(Redis) 도입 검토. |

---

### 스프린트 5 성공 메트릭

| 메트릭 | 기준 | 검증 방법 |
|--------|------|----------|
| Extension 저장 성공률 | 95% 이상 | 10개 다양한 사이트에서 저장 테스트 |
| Extension 본문 추출률 | 80% 이상 (일반 기사/블로그 기준) | 뉴스 사이트 5개, 블로그 5개, 기술 문서 5개 테스트 |
| 넛지 알림 수신 확인 | 3종 모두 정상 수신 | 수동 트리거 + 실제 크론 1회 검증 |
| 알림 클릭 -> 앱 이동 | 100% | 3종 알림 모두 클릭 시 해당 페이지 랜딩 확인 |
| 기존 기능 회귀 | 0건 | 통합 QA 체크리스트 전항 통과 |
| 파운더 1주 실사용 | 저녁 넛지로 저널 작성 빈도 증가 | dogfooding 1주간 저널 작성 횟수 Sprint 4 대비 비교 |

---

### 스프린트 5 진행 체크리스트

- [x] S5-0a: 기술 부채 정리 (DashboardView/GraphView 토스트, 히트맵 CSS 변수) (`0829704`)
- [x] S5-0b: 넛지 DB 스키마 (notification_settings, notification_log, push_subscription) (`0829704`)
- [x] S5-1: Extension 코드 리팩토링 (모듈화, 에러 핸들링) (`58035c0`)
- [x] S5-2: 페이지 본문 자동 추출 (content_script.js) (`58035c0`)
- [x] S5-3: 메모/태그 입력 UI (`58035c0`)
- [x] S5-4: 저장 완료 피드백 개선 (애니메이션, 자동 닫기) (`58035c0`)
- [x] S5-5: 알림 설정 API (GET/PATCH /settings/notifications) (`0829704`)
- [x] S5-6: Web Push 인프라 (Service Worker, pywebpush, VAPID) (`3b7cc37`)
- [x] S5-7: 컨텍스트 메뉴 + 키보드 단축키 저장 (`58035c0`)
- [x] S5-8: Extension 다크/라이트 테마 (`58035c0`)
- [x] S5-9: 저녁 회고 넛지 생성 로직 (`cae8dbb`)
- [x] S5-10: 주간 요약 넛지 생성 로직 (`cae8dbb`)
- [x] S5-11: 연결 발견 넛지 (벡터 유사도 기반) (`cae8dbb`)
- [x] S5-12: 넛지 전송 엔진 통합 (push + notification_log) (`cae8dbb`)
- [x] S5-13: Extension 통합 QA (`58035c0`)
- [x] S5-14: SettingsView 알림 설정 UI (`1d8414f`)
- [x] S5-15: 전체 통합 QA (브라우저 QA 전항 통과)
- [x] S5-16: 잔존 이슈 수정 (QA 통과로 이슈 0건)

---

### PM 최종 코멘트 (Sprint 5)

> Sprint 5는 Memoir 제품의 **성격을 근본적으로 전환**하는 스프린트다. 지금까지 Memoir는 "사용자가 찾아와야 하는 수동적 도구"였다. Sprint 5 이후에는 "사용자를 찾아가는 능동적 파트너"가 된다.
>
> Chrome Extension 개선은 수집 마찰을 "팝업 열기 → 저장 클릭"에서 "우클릭 → 저장" 또는 "단축키 한 번"으로 줄인다. 페이지 본문 자동 추출은 Librarian 에이전트가 더 풍부한 컨텍스트를 가지게 해주어, 요약/태깅/엔티티 추출 품질을 높인다.
>
> 넛지 시스템은 리텐션의 핵심이다. "오늘 3개의 새 기억이 쌓였습니다" 한 줄이 저녁 저널 작성률을 극적으로 높일 수 있다. 연결 발견 넛지는 Memoir만의 차별화 포인트 — "네가 저장한 것들 사이에 이런 연결이 있어"라고 말해주는 도구는 시장에 없다.

---

## 14. 스프린트 5 회고 (Retrospective)

**기간:** Sprint 5 (P2 Phase 3)
**회고일:** 2026-02-13
**완료 항목:** S5-0a~S5-16 (17/17 = 100% 완료)

### 14.1 Sprint 5 완료 사항 점검

| # | 작업 | 커밋 | 산출물 요약 | 품질 평가 |
|---|------|------|-----------|----------|
| S5-0a/0b | 기술 부채 + 넛지 DB | `0829704` | DashboardView/GraphView 토스트 연결, 히트맵 CSS 변수화. notification_settings/log/push_subscription 3개 테이블 + 알림 설정 CRUD API. | **백엔드 인프라 견고. 기존 부채 해소.** |
| S5-1~4/7/8/13 | Chrome Extension 전면 개선 | `58035c0` | content_script.js(Readability 기반 본문 추출), background.js(Service Worker, 컨텍스트 메뉴, Ctrl+Shift+M), 메모/태그 입력 UI, 다크/라이트 테마, 저장 애니메이션 | **7파일 신규/수정. 수집 마찰 대폭 감소.** |
| S5-6 | Web Push 인프라 | `3b7cc37` | sw.js(Service Worker Push 수신), pywebpush 통합, VAPID 키 생성, push_subscription API, usePushNotifications 훅 | **풀스택 Push 인프라 완성.** |
| S5-9~12 | 넛지 스케줄러 3종 + 전송 엔진 | `cae8dbb` | evening_review_job, weekly_summary_job, connection_discovery_job 3종 크론. send_nudge() 공통 전송 엔진. StatsService 재활용. | **4파일, 스케줄러 패턴 일관성 우수.** |
| S5-14 | SettingsView 알림 설정 UI | `1d8414f` | 알림 섹션 추가: 3종 넛지 토글, 저녁 회고 시간 선택(19~23시), 브라우저 푸시 권한 버튼. API 클라이언트(notifications.ts) + client.ts에 patch 함수 추가. | **4파일. 설정 UX 완결.** |
| S5-15/16 | 통합 QA | — | 정적 검증(TypeScript, 빌드, alert 0건, console.log 0건) + 브라우저 QA(Chat SSE, Memory CRUD, Journal, Dashboard, GraphView, Settings, Ctrl+K, 알림 API 4종) 전항 통과. 이슈 0건. | **QA 체크리스트 전항 PASS.** |

### 14.2 잘한 점 (Keep)

1. **양 끝단 전략 성공**: "입구(Extension) + 출구(넛지)" 양 끝단 강화 전략이 효과적. 두 트랙이 독립적으로 병렬 진행되어 5개 커밋에 17개 태스크 완료.

2. **기존 인프라 재활용**: APScheduler(Sprint 4), StatsService(Sprint 4), ToastContext(Sprint 1) 등 기존 인프라를 적극 재활용하여 신규 코드량 최소화.

3. **기술 부채 선행 정리**: Sprint 시작 시 TD-1~5를 먼저 정리(S5-0a)함으로써 이후 작업에서 부채가 누적되지 않는 패턴 확립.

4. **QA 무결**: 통합 QA에서 블로커 0건. Sprint 4 회고에서 지적된 "신규 컴포넌트에 토스트 미연결" 문제가 재발하지 않음.

### 14.3 개선점 (Improve)

1. **감정 분석 키워드 기반**: journal_service.py의 감정 분석이 키워드 매칭 기반(TODO: LLM/VADER 교체). 저널 AI 품질의 병목.

2. **카카오 실제 전송 미완**: scheduler_service.py, kakao_channel_service.py에 "TODO: 카카오 메시지 API로 실제 전송" 잔존. Push only 상태.

3. **메모리 편집 불가**: MemoryDetailModal이 조회/삭제만 지원. 태그 수정, 제목 수정이 불가하여 데이터 품질 관리에 한계.

4. **온보딩 부재**: P0-8(환영 배너)는 구현되었으나, 풀 온보딩 위자드가 없어 새 사용자가 기능을 발견하기 어려움.

5. **데이터 내보내기 없음**: 44개 API 중 Export 엔드포인트 0개. 사용자 데이터 주권 미확보.

### 14.4 Sprint 5 종합 평가

Sprint 5는 Memoir의 **"수동적 도구 → 능동적 파트너"** 전환을 성공적으로 달성했다. Chrome Extension은 수집 경로를 3가지(팝업 저장, 컨텍스트 메뉴, 키보드 단축키)로 확장했고, 넛지 시스템은 저녁 회고/주간 요약/연결 발견 3종을 Web Push로 전달하는 풀 파이프라인을 완성했다.

Sprint 1~5를 통해 P0~P2 전체가 완료되었으며, Phase 1("파운더가 매일 사용") + Phase 2("주변 지인이 사용 가능") 목표를 달성했다. 이제 Phase 3에 진입한다.

---

## 15. Phase 3 전략 재정의

### 15.1 원래 Phase 3 목표 vs 현실 제약

**원래 목표 (PRODUCT_REVIEW.md):**
> "외부 유저를 받을 준비가 된 상태" — 풀 온보딩 위자드, 랜딩 페이지, 초대 시스템, 리텐션 메트릭

**현실 제약:**
> 실제 외부 유저 모집이 불가한 상태. 초대 시스템과 성장 메트릭은 의미 없음.

### 15.2 재정의된 Phase 3 목표

**"서비스 유용성 극대화 + 제품 완성도 마무리"**

초점을 "유저 확보"에서 **"파운더가 진짜로 매일 의존하는 도구"**로 전환한다.

핵심 질문: *"지금 Memoir를 쓰면서 불편한 것, 아쉬운 것, 없으면 안 되는 것은 무엇인가?"*

Sprint 1~5 dogfogging에서 발견된 핵심 갭:

| # | 갭 | 영향 | 해결 Sprint |
|---|-----|------|------------|
| G-1 | 메모리 편집 불가 → 잘못된 태그/제목 수정 불가 → 데이터 품질 저하 | **높음** | Sprint 6 |
| G-2 | AI 대화가 참조한 메모리를 명시하지 않음 → "어디서 가져온 정보지?" 불신 | **높음** | Sprint 6 |
| G-3 | 저널과 메모리가 분리됨 → 회고 시 "내가 뭘 읽었더라" 수동 검색 필요 | **중간** | Sprint 6 |
| G-4 | 온보딩 부재 → 기능을 잊거나 발견 못함 | **중간** | Sprint 6 |
| G-5 | 접속하면 빈 채팅창 → "오늘 뭐하지?" 느낌 | **높음** | Sprint 6 |
| G-6 | 메모리가 쌓이면 정리 불가 (일괄 삭제/태그 없음) | **중간** | Sprint 6 |
| G-7 | 데이터 내보내기 없음 → 서비스 종속 불안 | **중간** | Sprint 7 |
| G-8 | 성능 미검증 (메모리 100개+ 시나리오) | **중간** | Sprint 7 |
| G-9 | 외부에 보여줄 랜딩 페이지 없음 | **낮음** | Sprint 7 |
| G-10 | PWA 미완성 → 모바일 즐겨찾기 불가 | **낮음** | Sprint 7 |

### 15.3 Sprint 6-7 전략 구조

```
┌─────────────────────────────────────────────────────────────────┐
│              Phase 3: 서비스 유용성 극대화 + 제품 완성도          │
│                                                                 │
│  Sprint 6: "매일 쓰고 싶은 서비스"                                │
│  ─────────────────────────────────                               │
│  초점: 파운더의 일상 워크플로우에서 발견된 마찰 제거               │
│  키워드: 편집, AI 신뢰, 연결, 발견, 정리                          │
│                                                                 │
│  Track A (데이터 관리)     Track B (AI + UX)                     │
│  ─────────────────────    ─────────────────────                  │
│  메모리 편집 기능           오늘의 브리핑 뷰                       │
│  메모리 일괄 관리           AI 대화 출처 표시                      │
│  데이터 품질 개선           풀 온보딩 위자드                       │
│                            저널 ↔ 메모리 연결 강화                │
│                                                                 │
│  Sprint 7: "보여줄 수 있는 완성품"                                │
│  ──────────────────────────────                                  │
│  초점: 장기 안정성 + 포트폴리오 수준의 마무리                      │
│  키워드: 내보내기, 성능, 안정성, 프레젠테이션                      │
│                                                                 │
│  Track A (사용자 가치)     Track B (인프라)                       │
│  ─────────────────────    ─────────────────────                  │
│  데이터 내보내기            성능 최적화                             │
│  랜딩 페이지               PWA 완성                               │
│  최종 UX 폴리싱            에러 모니터링 + 보안 강화               │
│                            최종 QA + 프로젝트 회고                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## 16. 스프린트 6 상세 계획 (Phase 3 전반: 서비스 유용성 극대화)

**목표:** "매일 쓰고 싶은 서비스" — 파운더의 일상 워크플로우 마찰 제거
**기간:** 약 12일 (10 작업일 + 2일 QA)
**선행 조건:** Sprint 5 완료 (전체 P0~P2 완료 상태)

### 전략적 배경

Sprint 1~5로 Memoir의 **기능 범위**는 9.0/10에 도달했다. 하지만 실제 dogfogging에서 체감하는 **기능 깊이**와 **워크플로우 완성도**에는 뚜렷한 갭이 있다. Sprint 6는 "새 기능 추가"가 아니라 **"기존 기능을 진짜 쓸 수 있게 만드는"** 스프린트다.

핵심 원칙:
1. **편집할 수 없는 데이터는 쓸모없다** — 메모리 편집 기능으로 데이터 품질 관리 가능하게
2. **AI는 출처를 밝혀야 신뢰된다** — 대화 응답에 참조 메모리를 명시하여 투명성 확보
3. **접속하면 바로 가치를 느껴야 한다** — "오늘의 브리핑"으로 즉시 유용한 정보 제공
4. **분리된 기능은 연결해야 의미있다** — 저널과 메모리의 양방향 링크로 지식 순환 완성

```
┌─────────────────────────────────────────────────────────────────┐
│                    스프린트 6 일정 계획                            │
│                                                                 │
│  Track A (데이터 관리)          Track B (AI + UX)                │
│  ─────────────────────────    ─────────────────────────          │
│  Day 1-2:                      Day 1-2:                         │
│  S6-1 메모리 편집 기능           S6-2 오늘의 브리핑 뷰             │
│  (PATCH API + 편집 모드 UI)     (DashboardView 개편)             │
│                                                                 │
│  Day 3-4:                      Day 3-4:                         │
│  S6-3 메모리 일괄 관리           S6-4 AI 대화 출처 표시            │
│  (다중 선택 + 일괄 작업)         (Socrates 응답에 참조 메모리)     │
│                                                                 │
│  Day 5-6:                      Day 5-7:                         │
│  S6-5 저널 ↔ 메모리 연결 강화   S6-6 풀 온보딩 위자드             │
│  (양방향 참조 시스템)            (3단계 가이드)                    │
│                                                                 │
│  Day 8:                                                         │
│  S6-7 기존 기능 보완 + 기술 부채                                  │
│                                                                 │
│  Day 9-10: S6-8 통합 QA                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

### S6-1: 메모리 편집 기능 (Day 1-2) — 풀스택

**문제:** 메모리를 조회/삭제만 가능. Librarian가 자동 태깅한 결과가 부정확해도 수정할 수 없어 데이터 품질이 시간이 갈수록 저하.

**해결:**

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | `PATCH /api/v1/memories/{memory_id}` | 수정 가능 필드: title, summary, tags. Pydantic 스키마에 Optional 필드. 수정 시 `updated_at` 타임스탬프 갱신. 태그 변경 시 KuzuDB 그래프 엔티티 동기화(기존 태그 노드 삭제 + 새 태그 노드 생성). |
| BE | 기존 태그 자동완성 API | `GET /api/v1/memories/tags?q=prefix` — 사용자의 기존 태그 목록에서 prefix 매칭. 프론트 자동완성 드롭다운용. |
| FE | MemoryDetailModal 편집 모드 | 모달 우상단 "편집" 버튼 클릭 → 인라인 편집 활성화. 제목: `contentEditable` div → input 전환. 태그: 기존 태그 칩에 X(삭제) 버튼 + 새 태그 입력 필드(자동완성). 요약: textarea 전환 (선택적). "저장" / "취소" 버튼 쌍. 저장 시 `PATCH` 호출 + `toast.success('메모리가 수정되었습니다')`. |
| FE | 메모리 목록 실시간 반영 | 편집 저장 후 MemoryView의 카드 목록이 즉시 갱신되도록 상태 관리. `loadMemories()` 재호출 또는 로컬 상태 업데이트. |

**체크포인트:**
- [ ] 메모리 상세 모달에서 제목 편집 후 저장 → 목록에 반영
- [ ] 태그 추가/삭제 후 저장 → 그래프뷰에서 태그 노드 갱신 확인
- [ ] 기존 태그 입력 시 자동완성 드롭다운 표시
- [ ] 편집 취소 시 원래 값 복원

---

### S6-2: 오늘의 브리핑 뷰 (Day 1-2) — 풀스택

**문제:** 접속하면 빈 채팅창. "오늘 뭐하지?"에 대한 답이 없어 즉각적인 가치를 체감하기 어려움. DashboardView에 스트릭/통계는 있지만 "오늘 할 일"을 제안하지 않음.

**해결:**

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | `GET /api/v1/briefing/today` | 오늘의 브리핑 데이터 통합 조회: (1) today_memories: 오늘 수집된 메모리 수 + 주요 토픽 3개, (2) unreviewed_count: 아직 저널에서 언급되지 않은 메모리 수, (3) streak: 현재 저널 스트릭, (4) suggested_question: AI가 생성한 오늘의 회고 질문 1개 (기존 review-questions API 재활용), (5) connection_hint: 최근 발견된 메모리 연결 1건 (nudge_service 로직 재활용). 응답은 가볍게(0.5초 이내). 캐시: 같은 날 같은 유저에게 5분 캐시. |
| FE | DashboardView "오늘의 브리핑" 섹션 | DashboardView 상단에 카드형 브리핑 섹션 추가. 4개 카드: (1) "오늘 {N}개의 새 기억" + 토픽 태그 → 클릭 시 MemoryView 이동, (2) "회고하지 않은 기억 {N}개" + CTA "저널 쓰러 가기" → JournalView 이동, (3) "오늘의 질문: {질문}" → 클릭 시 JournalView에 질문 전달, (4) "연결 발견: {A}와 {B}" → 클릭 시 메모리 상세. 기존 스트릭/통계는 하단으로 배치. |
| FE | ChatView 홈 화면 개편 | 채팅 세션이 없는(빈) ChatView에서 브리핑 요약 카드 표시. "오늘 {N}개 기억이 쌓였습니다. 무엇이 궁금하세요?" + 추천 질문 3개 버튼 (메모리 기반). 기존 WelcomeBanner와 통합/교체. |

**체크포인트:**
- [ ] DashboardView 접속 시 오늘의 브리핑 카드 4개 표시
- [ ] "저널 쓰러 가기" CTA 클릭 → JournalView 이동
- [ ] "오늘의 질문" 클릭 → JournalView에 질문 프리필
- [ ] 메모리 0개 상태에서도 적절한 빈 상태 메시지 (예: "첫 메모리를 추가해보세요!")
- [ ] ChatView 빈 상태에서 추천 질문 표시

---

### S6-3: 메모리 일괄 관리 (Day 3-4) — 풀스택

**문제:** 메모리가 쌓이면 정리가 필요하지만 개별 삭제/편집만 가능. 100개 이상 메모리를 하나씩 관리하는 것은 비현실적.

**해결:**

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | `POST /api/v1/memories/bulk` | 일괄 작업 API. body: `{ action: "delete" | "add_tags" | "remove_tags", memory_ids: string[], tags?: string[] }`. 삭제 시 벡터 임베딩 + KuzuDB 노드 일괄 정리. 트랜잭션으로 감싸서 원자성 보장. 최대 50개 제한 (rate limit). |
| FE | MemoryView 선택 모드 | "전체" 탭에 "선택" 토글 버튼 추가. 활성화 시 각 카드에 체크박스 표시. 헤더에 선택 카운트 + "전체 선택" 체크박스. 하단 플로팅 액션바: [삭제 ({N}개)] [태그 추가] [태그 제거] [취소]. 삭제: confirm 다이얼로그 → bulk API 호출 → `toast.success('{N}개 메모리가 삭제되었습니다')`. 태그 추가/제거: 태그 입력 모달(자동완성 포함) → bulk API 호출. |
| FE | 선택 모드 UX | 선택된 카드에 시각적 하이라이트(border-color 변경). Shift+클릭으로 범위 선택. Escape로 선택 모드 해제. 선택 상태에서 다른 탭 이동 시 선택 초기화. |

**체크포인트:**
- [ ] "선택" 토글 → 체크박스 표시 → 다중 선택 가능
- [ ] "전체 선택" 체크박스 동작
- [ ] 일괄 삭제: 3개 선택 → 삭제 → confirm → API 호출 → 목록 갱신 + 토스트
- [ ] 일괄 태그 추가: 2개 선택 → "태그 추가" → 태그 입력 → 적용 확인
- [ ] Escape로 선택 모드 해제

---

### S6-4: AI 대화 출처 표시 (Day 3-4) — 풀스택

**문제:** Socrates가 메모리를 참조해서 답변하지만 "어느 메모리를 참고했는지" 표시하지 않음. 사용자는 AI 답변의 근거를 알 수 없어 신뢰도가 낮음.

**해결:**

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | Socrates 응답에 참조 메모리 포함 | SSE 스트리밍 응답의 마지막에 `data: {"type": "references", "memories": [...]}` 이벤트 추가. 참조 메모리 정보: id, title, source_type, created_at. `_search_vector_memories()` 결과에서 실제 응답에 사용된 메모리를 추적하여 반환. 최대 5개 제한. 메모리 검색이 없었던(일반 대화) 경우 references 이벤트 생략. |
| FE | ChatView 참조 메모리 UI | AI 응답 메시지 하단에 "참조한 기억" 접이식 섹션 추가. 접힌 상태에서 "📎 {N}개 기억 참조" 레이블. 클릭 시 펼쳐져서 참조 메모리 칩(제목 + 소스 타입 아이콘) 나열. 칩 클릭 → MemoryDetailModal 열림. 일반 대화(참조 없음) 시 섹션 미표시. |
| FE | SSE 파서 확장 | 기존 SSE 파서가 `content` 이벤트만 처리. `references` 타입 이벤트 추가 파싱. 메시지 객체에 `references?: Memory[]` 필드 추가. |

**체크포인트:**
- [ ] "내가 저장한 AI 관련 글 요약해줘" 질문 → 응답 하단에 참조 메모리 표시
- [ ] 참조 메모리 칩 클릭 → 해당 메모리 상세 모달 열림
- [ ] 일반 대화 ("안녕하세요") → 참조 섹션 미표시
- [ ] 참조 메모리가 5개 이상일 때 최대 5개만 표시

---

### S6-5: 저널 ↔ 메모리 연결 강화 (Day 5-6) — 풀스택

**문제:** 저널 작성과 메모리 수집이 분리된 경험. 회고할 때 "내가 오늘 뭘 읽었더라"를 수동으로 검색해야 함. 역으로 메모리를 볼 때 "이 기억에 대해 뭘 썼더라"를 확인할 수 없음.

**해결:**

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | 저널-메모리 연결 추적 | `journal_memory_links` 테이블: journal_id, memory_id, link_type(cited/auto_suggested/manual), created_at. 저널 저장 시 `POST /journals/related-memories` 결과를 자동으로 링크 레코드 생성 (link_type: auto_suggested). 사용자가 명시적으로 메모리를 참조하면 (link_type: manual). |
| BE | 메모리→저널 역참조 API | `GET /api/v1/memories/{id}/journals` — 해당 메모리를 참조한 저널 목록 반환 (날짜, 제목/첫줄 미리보기). MemoryDetailModal에서 사용. |
| FE | JournalView 메모리 사이드바 강화 | 기존 MemorySidebar의 "관련 기억" 목록에 "이 기억 인용하기" 버튼 추가. 클릭 시 에디터에 해당 메모리 참조 블록 삽입 (Tiptap 커스텀 노드 또는 인라인 링크). 참조 블록: 메모리 제목 + 소스 타입 아이콘 + 클릭 시 상세 모달. |
| FE | MemoryDetailModal "관련 저널" 섹션 | 모달 하단에 "이 기억이 언급된 저널" 섹션 추가. 저널 항목: 날짜 + 미리보기 텍스트. 클릭 시 JournalView 해당 날짜로 이동. 연결 없으면 "아직 이 기억에 대해 작성한 저널이 없습니다" 빈 상태. |
| FE | 저널 저장 시 자동 링크 | 저널 저장(PATCH /journals) 시 현재 에디터 내용에서 참조된 메모리 ID를 추출 → 자동으로 journal_memory_links에 반영. |

**체크포인트:**
- [ ] JournalView 사이드바에서 "이 기억 인용하기" 클릭 → 에디터에 참조 블록 삽입
- [ ] 저널 저장 후 → 해당 메모리의 상세 모달에서 "관련 저널" 표시
- [ ] 메모리 상세에서 "관련 저널" 클릭 → JournalView 해당 날짜로 이동
- [ ] 연결이 없는 메모리에서 적절한 빈 상태 메시지

---

### S6-6: 풀 온보딩 위자드 (Day 5-7) — FE

**문제:** OAuth 로그인 후 바로 빈 ChatView로 진입. 제품이 무엇인지, 어떻게 사용하는지 안내 없음. P0-8(환영 배너)만으로는 기능 발견이 부족.

**해결:**

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | OnboardingWizard 컴포넌트 | 3단계 풀 온보딩. 모달 또는 전체 화면 오버레이. 스텝 인디케이터 (1/3, 2/3, 3/3). 각 단계에 "건너뛰기" 링크 + "다음" 버튼. |
| FE | Step 1: 환영 + 제품 소개 | "Memoir에 오신 것을 환영합니다!" 제목. 핵심 가치 3개 아이콘 카드: (1) 📚 수집 — "웹에서 읽은 글을 한 곳에 모으세요", (2) 💬 대화 — "AI와 대화하며 기억을 탐색하세요", (3) 📝 회고 — "하루를 돌아보며 저널을 작성하세요". 간결한 애니메이션 (fade-in 순차 등장). |
| FE | Step 2: 첫 메모리 추가 유도 | "먼저 기억을 하나 추가해볼까요?" 제목. 두 가지 옵션 카드: (1) "직접 입력하기" → 인라인 메모리 추가 폼 (URL 또는 텍스트), (2) "Chrome 확장 설치" → Extension 설치 페이지 링크. 추가 완료 시 축하 애니메이션 + "다음" 활성화. "나중에 하기" 옵션 제공. |
| FE | Step 3: 첫 대화 유도 | "Socrates에게 질문해보세요" 제목. 추천 질문 3개 버튼: (예: "최근 관심사에 대해 이야기해줘", "저장한 글 중 인상적인 것은?", "이번 주 내가 읽은 것들을 정리해줘"). 버튼 클릭 → ChatView로 이동 + 해당 질문 자동 전송. "완료" 버튼 → 온보딩 종료. |
| FE | 온보딩 상태 관리 | `localStorage.setItem('onboarding_completed', 'true')` + Supabase user_metadata에도 저장 (디바이스 간 동기화 가능하도록). 완료/건너뛴 사용자에게 재표시하지 않음. SettingsView에 "온보딩 다시 보기" 옵션 추가. |

**체크포인트:**
- [ ] 신규 사용자(onboarding_completed 없음) 로그인 시 → 온보딩 위자드 자동 표시
- [ ] Step 1 → Step 2 → Step 3 순차 진행 + 스텝 인디케이터 갱신
- [ ] Step 2에서 메모리 추가 시 축하 피드백
- [ ] Step 3에서 추천 질문 클릭 → ChatView로 이동 + 질문 전송
- [ ] "건너뛰기" → 온보딩 종료 + 재표시 안 됨
- [ ] SettingsView "온보딩 다시 보기" → 온보딩 재실행

---

### S6-7: 기존 기능 보완 + 기술 부채 (Day 8)

**문제:** Sprint 1~5에서 누적된 미세 이슈 + Sprint 6 신규 작업 과정에서 발견될 문제.

| # | 작업 | 담당 | 예상 | 상세 |
|---|------|------|------|------|
| S6-7a | 감정 분석 LLM 전환 | BE | 0.5d | journal_service.py의 키워드 기반 감정 분석을 LLM 호출로 교체. 기존 gpt-4o-mini 활용하여 저널 텍스트에서 감정 키워드 + 웰빙 점수 추출. TODO 해소. |
| S6-7b | ChatView 빈 채팅 개선 | FE | 0.3d | S6-2에서 추가한 추천 질문과 기존 WelcomeBanner 통합. 중복 제거 및 빈 상태 UX 일관성 확보. |
| S6-7c | 기술 부채 잔여분 정리 | ALL | 0.2d | Sprint 6 작업 중 발견된 코드 이슈 수정. 미사용 import 정리, 타입 오류 수정 등. |

---

### S6-8: 통합 QA (Day 9-10)

**통합 QA 체크리스트:**

메모리 편집:
- [ ] 제목 편집 → 저장 → 목록 반영
- [ ] 태그 추가/삭제 → 저장 → GraphView 동기화
- [ ] 요약 편집 → 저장 → 상세 모달에서 확인
- [ ] 편집 취소 시 원래 값 복원
- [ ] 태그 자동완성 동작

오늘의 브리핑:
- [ ] DashboardView 접속 시 브리핑 카드 표시
- [ ] 각 CTA 클릭 → 올바른 페이지 이동
- [ ] 메모리 0개 상태에서 적절한 빈 상태
- [ ] ChatView 빈 상태에서 추천 질문 표시

메모리 일괄 관리:
- [ ] 선택 모드 진입/해제
- [ ] 다중 선택 + 전체 선택
- [ ] 일괄 삭제 (confirm → 실행 → 토스트)
- [ ] 일괄 태그 추가/제거
- [ ] Shift+클릭 범위 선택

AI 출처 표시:
- [ ] 메모리 참조 응답 시 하단에 참조 메모리 표시
- [ ] 참조 메모리 칩 클릭 → 상세 모달
- [ ] 일반 대화 시 참조 섹션 미표시

저널 ↔ 메모리 연결:
- [ ] "이 기억 인용하기" → 에디터에 참조 블록 삽입
- [ ] 메모리 상세 → "관련 저널" 표시
- [ ] 저널 저장 후 자동 링크 생성

온보딩 위자드:
- [ ] 신규 사용자 → 위자드 자동 표시
- [ ] 3단계 순차 진행 + 건너뛰기
- [ ] Step 2 메모리 추가 시 축하
- [ ] Step 3 추천 질문 → ChatView 이동
- [ ] SettingsView "온보딩 다시 보기"

기존 기능 회귀:
- [ ] Chat SSE 스트리밍 정상
- [ ] 메모리 CRUD + 검색 정상
- [ ] 저널 작성/자동저장/히스토리 정상
- [ ] 대시보드 스트릭/통계/히트맵 정상
- [ ] 글로벌 검색 Ctrl+K 정상
- [ ] GraphView 노드 클릭/검색 정상
- [ ] 넛지 알림 정상

---

### 스프린트 6 파일별 수정 매핑

```
=== S6-1 메모리 편집 ===
수정:
  backend/app/routers/memory_router.py          ← PATCH /memories/{id}
  backend/app/services/memory_service.py        ← 수정 로직 + 그래프 동기화
  backend/app/repositories/memory_repository.py ← UPDATE 쿼리
  frontend/src/components/MemoryDetailModal.tsx  ← 편집 모드 UI
  frontend/src/components/MemoryDetailModal.css  ← 편집 모드 스타일
  frontend/src/api/client.ts                    ← (patch 함수 이미 존재)
신규:
  backend/app/routers/memory_router.py          ← GET /memories/tags (태그 자동완성)

=== S6-2 오늘의 브리핑 ===
신규:
  backend/app/routers/briefing_router.py        ← GET /briefing/today
  backend/app/services/briefing_service.py      ← 브리핑 데이터 통합 조회
  frontend/src/api/briefing.ts                  ← 브리핑 API 클라이언트
수정:
  backend/app/routers/router.py                 ← briefing_router 등록
  frontend/src/components/DashboardView.tsx     ← 브리핑 섹션 추가
  frontend/src/components/DashboardView.css     ← 브리핑 카드 스타일
  frontend/src/components/ChatView.tsx          ← 빈 상태 추천 질문

=== S6-3 메모리 일괄 관리 ===
수정:
  backend/app/routers/memory_router.py          ← POST /memories/bulk
  backend/app/services/memory_service.py        ← 일괄 삭제/태그 로직
  frontend/src/components/MemoryView.tsx        ← 선택 모드 UI
  frontend/src/MemoryView.css                   ← 선택 모드 스타일

=== S6-4 AI 출처 표시 ===
수정:
  backend/app/agents/socrates/nodes/chat.py     ← 참조 메모리 추적 + SSE 이벤트
  frontend/src/components/ChatView.tsx          ← 참조 메모리 UI + SSE 파서 확장
  frontend/src/ChatView.css                     ← 참조 섹션 스타일

=== S6-5 저널 ↔ 메모리 연결 ===
신규:
  backend/app/repositories/journal_memory_repository.py  ← 연결 CRUD
수정:
  backend/app/routers/memory_router.py          ← GET /memories/{id}/journals
  backend/app/routers/journal_router.py         ← 저장 시 자동 링크
  frontend/src/components/journal/MemorySidebar.tsx  ← "인용하기" 버튼
  frontend/src/components/MemoryDetailModal.tsx  ← "관련 저널" 섹션
  frontend/src/components/JournalView.tsx       ← 저널 저장 시 링크 생성

=== S6-6 온보딩 위자드 ===
신규:
  frontend/src/components/OnboardingWizard.tsx  ← 3단계 위자드
  frontend/src/components/OnboardingWizard.css  ← 위자드 스타일
수정:
  frontend/src/App.tsx                          ← 온보딩 조건부 렌더링
  frontend/src/components/SettingsView.tsx      ← "온보딩 다시 보기" 옵션
  frontend/src/components/ChatView.tsx          ← WelcomeBanner 통합

=== S6-7 기술 부채 ===
수정:
  backend/app/services/journal_service.py       ← 감정 분석 LLM 전환
```

---

### 스프린트 6 의존성 그래프

```
S6-1 (메모리 편집) ─────────────────────── 독립
S6-2 (브리핑 뷰) ──────────────────────── 독립
S6-3 (일괄 관리) ──────────────────────── 독립 (S6-1의 태그 API 재활용 가능)
S6-4 (AI 출처) ────────────────────────── 독립

S6-1 (메모리 편집) ──┐
S6-4 (AI 출처)  ─────┼──> S6-5 (저널↔메모리 연결)
                     │    (편집된 메모리가 저널에서 참조 가능)
                     │
S6-2 (브리핑 뷰) ────┘──> S6-6 (온보딩 위자드)
                          (브리핑이 있어야 온보딩 Step 마지막에서 유도 가능)

S6-5 + S6-6 ─────────────> S6-7 (기술 부채 + 통합 보완)
전체 ────────────────────> S6-8 (통합 QA)
```

---

### 스프린트 6 리스크 및 대응

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| 메모리 편집 시 KuzuDB 태그 동기화 실패 | 그래프 데이터 불일치 | 중 | 태그 동기화를 try-catch로 감싸고, 실패 시 비동기 재시도 큐. 그래프 데이터는 보조적이므로 메모리 본체 수정은 항상 성공시킴. |
| Socrates 참조 메모리 추적의 정확도 | AI 답변과 무관한 메모리 표시 | 중 | 검색 결과 중 실제 응답 생성에 context로 전달된 메모리만 필터링. 검색했지만 사용하지 않은 메모리는 제외. |
| 온보딩 위자드가 기존 라우팅과 충돌 | 무한 리다이렉트 | 낮 | 온보딩을 라우트가 아닌 모달 오버레이로 구현. 기존 라우팅에 영향 없음. |
| 브리핑 API 응답 느림 (5개 데이터 소스 통합) | DashboardView 로딩 지연 | 중 | 병렬 Promise.all로 5개 쿼리 동시 실행. 개별 실패 시 해당 카드만 스켈레톤 유지. 5분 캐시로 반복 접속 시 즉시 응답. |
| 저널↔메모리 링크 테이블 마이그레이션 | DB 스키마 변경 | 낮 | 새 테이블 생성만 필요 (기존 테이블 수정 없음). Supabase 마이그레이션으로 안전 적용. |

---

### 스프린트 6 성공 메트릭

| 메트릭 | 기준 | 검증 방법 |
|--------|------|----------|
| 메모리 편집 완결성 | 제목/태그/요약 3개 필드 모두 수정 가능 | 실제 메모리 수정 후 목록/그래프 반영 확인 |
| 브리핑 즉시 가치 | 접속 후 3초 이내 "오늘 할 일" 인지 | DashboardView 로딩 시간 측정 + 카드 렌더링 |
| AI 출처 신뢰도 | 참조 메모리가 실제 응답 내용과 관련 | 10개 메모리 기반 질문 → 참조 정확도 수동 검증 |
| 저널↔메모리 연결 | 양방향 탐색 가능 | 저널에서 메모리 인용 → 메모리에서 역참조 확인 |
| 온보딩 완주율 | 3단계 중 Step 2까지 도달 | 온보딩 로그 (localStorage 기반) |
| 기존 기능 회귀 | 0건 | 통합 QA 체크리스트 전항 통과 |

---

### 스프린트 6 진행 체크리스트

- [ ] S6-1: 메모리 편집 기능 (PATCH API + 편집 모드 UI + 태그 자동완성)
- [ ] S6-2: 오늘의 브리핑 뷰 (브리핑 API + DashboardView 개편 + ChatView 빈 상태)
- [ ] S6-3: 메모리 일괄 관리 (bulk API + 선택 모드 + 일괄 삭제/태그)
- [ ] S6-4: AI 대화 출처 표시 (Socrates 참조 추적 + ChatView 참조 UI)
- [ ] S6-5: 저널 ↔ 메모리 연결 강화 (양방향 링크 + 인용 블록 + 역참조)
- [ ] S6-6: 풀 온보딩 위자드 (3단계 가이드 + 메모리 추가 유도 + 대화 유도)
- [ ] S6-7: 기존 기능 보완 + 기술 부채 (감정 분석 LLM, 빈 상태 통합)
- [ ] S6-8: 통합 QA

---

## 17. 스프린트 7 상세 계획 (Phase 3 후반: 제품 완성도 마무리)

**목표:** "보여줄 수 있는 완성품" — 장기 안정성 + 포트폴리오 수준 마무리
**기간:** 약 10일 (8 작업일 + 2일 최종 QA)
**선행 조건:** Sprint 6 완료

### 전략적 배경

Sprint 6로 **서비스 유용성**이 극대화되었다면, Sprint 7은 **"이 제품을 외부에 보여줄 수 있는가?"**에 답하는 스프린트다. 포트폴리오, 발표, 데모 시연 시 자신있게 보여줄 수 있는 수준의 완성도를 확보한다.

핵심 원칙:
1. **데이터 주권 보장** — 내보내기 기능으로 사용자가 자신의 데이터를 소유
2. **성능은 기능이다** — 데이터가 쌓여도 느려지지 않는 것이 사용성의 핵심
3. **첫인상이 중요하다** — 랜딩 페이지로 제품의 가치를 한눈에 전달
4. **안정성은 신뢰다** — 에러 모니터링과 보안으로 프로덕션 수준 신뢰도 확보

```
┌─────────────────────────────────────────────────────────────────┐
│                    스프린트 7 일정 계획                            │
│                                                                 │
│  Track A (사용자 가치)          Track B (인프라 + 안정성)         │
│  ─────────────────────────    ─────────────────────────          │
│  Day 1-2:                      Day 1:                           │
│  S7-1 데이터 내보내기            S7-2 성능 최적화                  │
│  (Export API + UI)              (서버 캐싱 + 쿼리 최적화)         │
│                                                                 │
│  Day 3-4:                      Day 2-3:                         │
│  S7-3 랜딩 페이지               S7-4 PWA 완성                    │
│  (제품 소개 + 데모)              (manifest + 오프라인 기본)        │
│                                                                 │
│  Day 5:                        Day 4-5:                         │
│  S7-5 최종 UX 폴리싱            S7-6 에러 모니터링 + 보안 강화     │
│  (마이크로 인터랙션)             (Sentry-lite + rate limit)       │
│                                                                 │
│  Day 6-8: S7-7 최종 통합 QA + 프로젝트 회고                      │
└─────────────────────────────────────────────────────────────────┘
```

---

### S7-1: 데이터 내보내기 (Day 1-2) — 풀스택

**문제:** 44개 API 중 Export 엔드포인트 0개. 사용자가 자신의 데이터를 내려받을 수 없어 서비스 종속에 대한 불안감.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | `GET /api/v1/export/memories` | 사용자의 전체 메모리를 JSON으로 내보내기. 필드: id, title, summary, content, tags, source_url, source_type, created_at, updated_at. 페이지네이션 없이 전체 반환 (최대 10,000건). Content-Disposition 헤더로 파일 다운로드 유도. |
| BE | `GET /api/v1/export/journals` | 전체 저널을 Markdown ZIP으로 내보내기. 각 저널 = 하나의 .md 파일 (파일명: YYYY-MM-DD.md). 메타데이터(태그, 감정) YAML frontmatter로 포함. ZIP 스트리밍 응답. |
| BE | `GET /api/v1/export/all` | 전체 데이터 통합 내보내기 (JSON). memories + journals + chat_sessions + graph_data 포함. 백업/마이그레이션용. |
| FE | SettingsView "데이터 관리" 섹션 | "내보내기" 카드: 3종 버튼 (기억 JSON / 저널 Markdown / 전체 백업). 각 버튼 클릭 → 다운로드 시작 + `toast.info('내보내기를 준비하고 있습니다...')` → 완료 시 `toast.success('다운로드가 시작됩니다')`. 파일 크기 미리보기 (메모리 N개, 저널 N개). |

**체크포인트:**
- [ ] "기억 내보내기" → JSON 파일 다운로드 (올바른 구조)
- [ ] "저널 내보내기" → ZIP 파일 (날짜별 .md 파일)
- [ ] "전체 백업" → 통합 JSON 파일
- [ ] 메모리 0개 상태에서 적절한 빈 상태 (빈 파일 생성 안 함)
- [ ] 대용량 (100개+ 메모리) 시 타임아웃 없이 완료

---

### S7-2: 성능 최적화 (Day 1-3) — 풀스택

**문제:** 현재 캐싱 없음 (localStorage 드래프트만 존재). 메모리가 100개 이상 쌓이면 목록 조회, 벡터 검색, 그래프 로딩이 느려질 수 있음.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | 서버 사이드 인메모리 캐시 | `cachetools.TTLCache`로 자주 조회되는 데이터 캐싱: (1) 대시보드 통계: 5분 TTL, (2) 브리핑 데이터: 5분 TTL, (3) 태그 목록: 10분 TTL, (4) 그래프 데이터: 5분 TTL. 메모리 CUD 작업 시 관련 캐시 무효화. 사용자별 키 격리 (f"user:{user_id}:stats"). |
| BE | 쿼리 최적화 | (1) 메모리 목록 조회에 `SELECT` 필드 제한 (content 제외, 목록에서 불필요), (2) 통계 쿼리에 Supabase RPC (SQL 함수)로 왕복 줄이기, (3) 그래프 데이터 조회 시 노드 수 제한 (최대 500개, 이후 페이지네이션). |
| FE | 프론트엔드 최적화 | (1) React.memo로 MemoryCard, ChatMessage 등 빈번한 리렌더 컴포넌트 최적화, (2) MemoryView 가상 스크롤 도입 (react-window 또는 IntersectionObserver 개선), (3) 이미지/아이콘 레이지 로딩, (4) 번들 사이즈 분석 (vite-bundle-visualizer) + 코드 스플리팅 확인. |

**체크포인트:**
- [ ] 메모리 100개 시 목록 로딩 2초 이내
- [ ] 대시보드 반복 접속 시 캐시 히트 (네트워크 요청 감소 확인)
- [ ] 그래프 노드 200개 이상에서 렌더링 성능 확인 (30fps 이상)
- [ ] 번들 사이즈 리포트 생성 + 불필요한 대형 의존성 식별

---

### S7-3: 랜딩 페이지 (Day 3-4) — FE

**문제:** 외부에 보여줄 제품 소개 페이지가 없음. 로그인 화면만 있어 "이게 뭔 서비스지?" 첫인상 부재.

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | `/` 랜딩 페이지 라우트 | 비로그인 사용자가 `/`에 접속하면 랜딩 페이지 표시. 로그인 사용자는 `/chat`으로 리다이렉트 (기존 동작 유지). |
| FE | Hero 섹션 | "당신의 기억을 지키는 AI 파트너" 헤드라인. 3줄 서브 텍스트: 핵심 가치 전달. [시작하기] CTA 버튼 → `/login`. 배경: 기존 디자인 토큰 활용한 그래디언트 또는 패턴. |
| FE | 기능 소개 섹션 | 4개 기능 카드 (수집 / 대화 / 저널 / 그래프). 각 카드: 아이콘(Lucide) + 제목 + 2줄 설명. 스크린샷 또는 모의 UI 이미지 (선택적). 기존 CSS 변수 + 디자인 토큰 활용. |
| FE | 기술 스택 섹션 (선택) | "Built with" — React, FastAPI, LangGraph, Supabase 등 기술 스택 로고. 포트폴리오 어필용. |
| FE | Footer | 저작권 표시 + GitHub 링크 (있는 경우). 미니멀한 디자인. |

**체크포인트:**
- [ ] 비로그인 상태에서 `/` → 랜딩 페이지 표시
- [ ] 로그인 상태에서 `/` → `/chat` 리다이렉트
- [ ] Hero CTA "시작하기" → `/login` 이동
- [ ] 라이트/다크 모드 모두에서 정상 표시
- [ ] 모바일 반응형 (767px 이하) 정상

---

### S7-4: PWA 완성 (Day 2-3) — FE

**문제:** Service Worker는 Push 전용으로만 존재. manifest.json 없음. 모바일에서 홈 화면 추가 불가. 오프라인 기본 지원 없음.

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | manifest.json 생성 | name: "Memoir", short_name: "Memoir", start_url: "/", display: "standalone", theme_color/background_color: 디자인 토큰 참조. icons: 192x192, 512x512 PNG (기존 favicon 확대 또는 신규). |
| FE | Service Worker 오프라인 기본 | 기존 sw.js 확장: (1) install 이벤트에서 앱 셸 캐시 (index.html, CSS, JS 번들), (2) fetch 이벤트에서 네트워크 우선 + 캐시 폴백 전략 (stale-while-revalidate), (3) 오프라인 시 "인터넷 연결을 확인해주세요" 폴백 페이지. |
| FE | index.html 메타 태그 | `<link rel="manifest" href="/manifest.json">`, `<meta name="theme-color">`, `<meta name="apple-mobile-web-app-capable">`, 아이콘 링크. |
| FE | 설치 프롬프트 | `beforeinstallprompt` 이벤트 감지. SettingsView에 "앱 설치하기" 버튼 (조건: 미설치 + 프롬프트 가능 상태). |

**체크포인트:**
- [ ] Chrome DevTools → Application → Manifest 정상 표시
- [ ] Lighthouse PWA 점수 측정
- [ ] 모바일 Chrome에서 "홈 화면에 추가" 가능
- [ ] 오프라인 시 폴백 페이지 표시 (앱 크래시 아님)
- [ ] SettingsView "앱 설치하기" 버튼 조건부 표시

---

### S7-5: 최종 UX 폴리싱 (Day 5) — FE

**문제:** 기능은 완성되었으나 마이크로 인터랙션, 전환 애니메이션, 로딩 스켈레톤 등 "느낌"을 결정하는 디테일 부족.

| # | 작업 | 상세 |
|---|------|------|
| S7-5a | 로딩 스켈레톤 | MemoryView 카드, DashboardView 통계, JournalView 에디터 영역에 콘텐츠 로딩 시 스켈레톤 UI 적용. `@keyframes shimmer` 기반 CSS-only 스켈레톤. |
| S7-5b | 페이지 전환 애니메이션 | React Router에 간단한 fade-in 전환 (CSS transition 기반). 200ms opacity 전환. 과도하지 않게 미니멀하게. |
| S7-5c | 마이크로 인터랙션 | 버튼 클릭 시 ripple 또는 scale 효과. 토스트 등장/소멸 애니메이션 개선 (slide-up). 메모리 카드 hover 시 미세 lift 효과. |
| S7-5d | 다크/라이트 전환 애니메이션 | 테마 전환 시 `transition: background-color 0.3s, color 0.3s` 전체 적용. 깜빡임 없는 부드러운 전환. |

**체크포인트:**
- [ ] 메모리 목록 로딩 중 스켈레톤 표시 (깜빡임 없음)
- [ ] 페이지 이동 시 부드러운 전환
- [ ] 다크↔라이트 전환 시 부드러운 색상 변환
- [ ] 전체적인 "느낌"이 완성도 있는지 주관적 평가

---

### S7-6: 에러 모니터링 + 보안 강화 (Day 4-5) — 풀스택

**문제:** 에러가 서버 로그에만 기록되고, API rate limiting 없음. 프로덕션 배포 시 안정성 미확보.

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | 글로벌 에러 바운더리 | React ErrorBoundary 컴포넌트: 예기치 않은 렌더링 에러 캐치. "문제가 발생했습니다" 폴백 UI + "새로고침" 버튼. 에러 정보를 `console.error` + 선택적으로 서버 전송 (`POST /api/v1/errors`). window.onerror, unhandledrejection 이벤트 리스너 추가. |
| BE | 에러 리포팅 엔드포인트 | `POST /api/v1/errors` — 프론트엔드 에러 수집. 필드: message, stack, url, user_agent, timestamp. 파일 기반 로깅 (errors.log) + 향후 외부 서비스 연동 포인트. |
| BE | API Rate Limiting | `slowapi` 라이브러리로 주요 엔드포인트에 rate limit 적용. 기본: 60req/min per user. LLM 호출 엔드포인트: 10req/min (chat, journal AI). 메모리 생성: 30req/min. 429 응답 시 프론트에서 적절한 토스트 표시. |
| BE | 입력 검증 강화 | Pydantic 모델에 필드 길이 제한 추가: title max 200자, summary max 2000자, content max 50000자, tags 최대 20개/태그당 50자. SQL injection 방지: Supabase 파라미터 바인딩 재확인. |
| BE | CORS 정책 강화 | DEBUG=False 시 allow_origins를 실제 프로덕션 도메인으로 제한 (현재 `*`). 환경변수 `ALLOWED_ORIGINS`로 설정. |

**체크포인트:**
- [ ] 프론트엔드 에러 발생 시 ErrorBoundary 폴백 UI 표시
- [ ] Rate limit 초과 시 429 응답 + 토스트 표시
- [ ] 제목 200자 초과 입력 시 422 검증 에러
- [ ] CORS: 프로덕션 모드에서 허용 도메인만 접근 가능

---

### S7-7: 최종 통합 QA + 프로젝트 회고 (Day 6-8)

**최종 QA 체크리스트:**

데이터 내보내기:
- [ ] 기억 JSON 내보내기 → 유효한 JSON 구조
- [ ] 저널 Markdown ZIP → 날짜별 .md 파일 존재
- [ ] 전체 백업 → memories + journals + sessions 포함
- [ ] 대용량 시나리오 (100개+) 타임아웃 없음

성능:
- [ ] 메모리 100개 목록 로딩 ≤ 2초
- [ ] 대시보드 반복 접속 캐시 히트
- [ ] 그래프 200노드 렌더링 30fps+
- [ ] 번들 사이즈 확인 (초기 로딩 ≤ 3초)

랜딩 페이지:
- [ ] 비로그인 `/` → 랜딩 페이지
- [ ] CTA → `/login` 이동
- [ ] 라이트/다크 모드
- [ ] 모바일 반응형

PWA:
- [ ] manifest.json Lighthouse 검증
- [ ] 오프라인 폴백 페이지
- [ ] 모바일 "홈 화면 추가"

UX 폴리싱:
- [ ] 스켈레톤 로딩 (MemoryView, DashboardView)
- [ ] 페이지 전환 애니메이션
- [ ] 테마 전환 애니메이션

보안 + 안정성:
- [ ] ErrorBoundary 폴백 UI
- [ ] Rate limit 429 처리
- [ ] 입력 검증 (길이 제한)
- [ ] CORS 프로덕션 모드

전체 기능 회귀 (Sprint 1~6):
- [ ] Chat SSE 스트리밍
- [ ] 메모리 CRUD + 편집 + 검색 + 일괄 관리
- [ ] 저널 작성/자동저장/히스토리
- [ ] 대시보드 브리핑 + 스트릭/통계
- [ ] 글로벌 검색 Ctrl+K
- [ ] GraphView 노드 클릭/검색
- [ ] 넛지 알림
- [ ] Chrome Extension
- [ ] 온보딩 위자드
- [ ] AI 출처 표시
- [ ] 저널↔메모리 연결
- [ ] 데이터 내보내기

**프로젝트 회고 (Sprint 7 Day 8):**
- Sprint 1~7 전체 회고
- 종합 점수표 최종 업데이트
- 남은 기술 부채 목록 정리
- 향후 로드맵 제안 (Phase 4 이후)

---

### 스프린트 7 파일별 수정 매핑

```
=== S7-1 데이터 내보내기 ===
신규:
  backend/app/routers/export_router.py          ← GET /export/memories, /journals, /all
  backend/app/services/export_service.py        ← JSON/Markdown/ZIP 생성 로직
  frontend/src/api/export.ts                    ← 내보내기 API 클라이언트
수정:
  backend/app/routers/router.py                 ← export_router 등록
  frontend/src/components/SettingsView.tsx      ← "데이터 관리" 섹션 추가
  frontend/src/components/SettingsView.css      ← 내보내기 버튼 스타일

=== S7-2 성능 최적화 ===
수정:
  backend/app/services/stats_service.py         ← TTL 캐시 적용
  backend/app/services/briefing_service.py      ← TTL 캐시 적용
  backend/app/services/graph_service.py         ← 노드 수 제한 + 캐시
  backend/app/repositories/memory_repository.py ← SELECT 필드 최적화
  frontend/src/components/MemoryView.tsx        ← React.memo + 가상 스크롤
  frontend/src/components/ChatView.tsx          ← ChatMessage React.memo
신규:
  backend/app/utils/cache.py                    ← TTL 캐시 유틸리티

=== S7-3 랜딩 페이지 ===
신규:
  frontend/src/components/LandingPage.tsx       ← 랜딩 페이지 컴포넌트
  frontend/src/components/LandingPage.css       ← 랜딩 스타일
수정:
  frontend/src/App.tsx                          ← '/' 라우트 조건부 렌더링

=== S7-4 PWA ===
신규:
  frontend/public/manifest.json                 ← PWA 매니페스트
  frontend/public/icons/                        ← 192x192, 512x512 아이콘
수정:
  frontend/public/sw.js                         ← 오프라인 캐시 전략 추가
  frontend/index.html                           ← manifest 링크, 메타 태그
  frontend/src/components/SettingsView.tsx      ← "앱 설치하기" 버튼

=== S7-5 UX 폴리싱 ===
수정:
  frontend/src/index.css                        ← 스켈레톤 키프레임, 전환 애니메이션
  frontend/src/components/MemoryView.tsx        ← 스켈레톤 로딩
  frontend/src/components/DashboardView.tsx     ← 스켈레톤 로딩
  frontend/src/App.tsx                          ← 페이지 전환 래퍼

=== S7-6 에러 모니터링 + 보안 ===
신규:
  frontend/src/components/ErrorBoundary.tsx     ← React ErrorBoundary
  backend/app/routers/error_router.py           ← POST /errors
  backend/app/utils/rate_limiter.py             ← slowapi 설정
수정:
  backend/app/main.py                           ← rate limiter 미들웨어, CORS 강화
  backend/app/routers/router.py                 ← error_router 등록
  backend/app/schemas/memory_schema.py          ← 필드 길이 제한
  frontend/src/App.tsx                          ← ErrorBoundary 래핑
  frontend/src/components/ChatView.tsx          ← 429 에러 토스트
```

---

### 스프린트 7 의존성 그래프

```
S7-1 (내보내기) ────────────────────────── 독립
S7-2 (성능) ───────────────────────────── 독립
S7-3 (랜딩 페이지) ────────────────────── 독립
S7-4 (PWA) ────────────────────────────── 독립

S7-5 (UX 폴리싱) ──────────────────────── 모든 기능 작업 완료 후
S7-6 (보안) ────────────────────────────── 독립 (단, 최종 QA 전)

전체 ──> S7-7 (최종 QA + 프로젝트 회고)
```

---

### 스프린트 7 리스크 및 대응

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| 대용량 내보내기 메모리 부족 | 서버 OOM | 낮 | 스트리밍 응답으로 메모리 최적화. 10,000건 제한. |
| Service Worker 캐시 무효화 문제 | 구버전 앱 사용 | 중 | 버전 기반 캐시 키. 새 배포 시 skipWaiting + clients.claim. |
| slowapi rate limiter가 Fly.io에서 동작 안 함 | 보안 미적용 | 낮 | in-memory 기반이므로 단일 인스턴스에서 동작. 분산 환경 시 Redis 백엔드. |
| 랜딩 페이지 디자인 품질 미달 | 첫인상 저하 | 중 | 기존 디자인 토큰 최대 활용. 미니멀한 디자인으로 범위 제한. |
| 번들 사이즈 비대 (react-force-graph-3d 등) | 초기 로딩 느림 | 중 | GraphView를 React.lazy로 동적 import. three.js 번들 분리. |

---

### 스프린트 7 성공 메트릭

| 메트릭 | 기준 | 검증 방법 |
|--------|------|----------|
| 데이터 내보내기 | 3종 모두 유효한 파일 생성 | 내보낸 JSON 파싱 + Markdown 렌더링 확인 |
| 성능 | 메모리 100개 기준 목록 ≤ 2초, 그래프 ≤ 3초 | Chrome DevTools Performance 패널 |
| Lighthouse 점수 | Performance ≥ 70, PWA ≥ 80 | Lighthouse 자동 측정 |
| 에러 복구 | 에러 시 앱 크래시 0건 | ErrorBoundary로 모든 에러 포착 확인 |
| 보안 | Rate limit 동작 + CORS 제한 | curl로 60+req/min 요청 시 429 확인 |
| 기존 기능 회귀 | 0건 | 최종 QA 체크리스트 전항 통과 |

---

### 스프린트 7 진행 체크리스트

- [ ] S7-1: 데이터 내보내기 (Export API 3종 + SettingsView UI)
- [ ] S7-2: 성능 최적화 (서버 캐시 + 쿼리 최적화 + React.memo + 번들 분석)
- [ ] S7-3: 랜딩 페이지 (Hero + 기능 소개 + 반응형)
- [ ] S7-4: PWA 완성 (manifest + 오프라인 + 설치 프롬프트)
- [ ] S7-5: 최종 UX 폴리싱 (스켈레톤 + 전환 + 마이크로 인터랙션)
- [ ] S7-6: 에러 모니터링 + 보안 강화 (ErrorBoundary + rate limit + CORS)
- [ ] S7-7: 최종 통합 QA + 프로젝트 회고

---

## 18. Phase 3 완료 후 예상 제품 상태

### 18.1 종합 점수표 (예상)

| 평가 항목 | Sprint 1 시작 | Sprint 5 완료 | Sprint 7 완료 (예상) | 변화 |
|-----------|:----------:|:----------:|:----------------:|:----:|
| 기능 범위 | 7.4 | 9.0 | **9.5** | +0.5 |
| 기능 깊이 | 5.4 | 7.5 | **8.5** | +1.0 |
| UX 완성도 | 4.3 | 7.0 | **8.5** | +1.5 |
| 코드 품질 | 7.5 | 8.0 | **8.5** | +0.5 |
| PMF 준비도 | 3.3 | 6.5 | **8.0** | +1.5 |

### 18.2 Sprint 7 완료 시 제품 상태

```
"언제 누가 봐도 괜찮은, 파운더가 실제로 매일 의존하는 도구"

✅ 수집: Chrome Extension (3종 수집) + 웹 직접 입력 + 카카오톡
✅ 정리: Librarian AI 자동 분류/요약/태깅 + 사용자 편집
✅ 대화: Socrates AI (자동 의도 분류 + 출처 표시 + 맥락 유지)
✅ 회고: 저널 (AI 회고 질문 + 템플릿 + 메모리 양방향 연결)
✅ 발견: GraphView (3D 시각화 + 상호작용) + 연결 발견 넛지
✅ 리텐션: 대시보드 (브리핑 + 스트릭) + 넛지 3종 (Push)
✅ 온보딩: 3단계 풀 위자드
✅ 데이터: 내보내기 3종 (JSON/Markdown/전체 백업)
✅ 성능: 서버 캐시 + 쿼리 최적화 + 프론트 메모이제이션
✅ 안정성: ErrorBoundary + Rate Limit + CORS + 입력 검증
✅ PWA: 오프라인 기본 + 모바일 설치 + Web Push
✅ 랜딩: 제품 소개 + 기술 스택 + CTA
```

### 18.3 Memoir 최종 아키텍처 (Sprint 7 완료 기준)

```
프론트엔드: React 18 + TypeScript + Vite
  - 9개 주요 컴포넌트: ChatView, MemoryView, JournalView, GraphView,
    DashboardView, SettingsView, AuthView, LandingPage, OnboardingWizard
  - 글로벌 인프라: Toast, Theme, Auth Context + ErrorBoundary + CommandPalette
  - PWA: manifest.json, Service Worker (Push + 오프라인 캐시)
  - 성능: React.memo, lazy loading, 스켈레톤 UI

백엔드: FastAPI + Python
  - 11개 라우터: memory, chat, journal, search, digest, graph, stats,
    integrations, settings, briefing, export + error + push
  - 에이전트: Socrates (대화 + 자동 의도 + 출처 추적), Librarian (메모리 처리)
  - 인프라: APScheduler (다이제스트 + 넛지 크론), 서버 TTL 캐시
  - 보안: JWT 인증, user_id 필터, Rate Limiting, CORS 강화, 입력 검증

Chrome Extension: v1.2
  - Google OAuth, 페이지 본문 추출, 메모/태그, 컨텍스트 메뉴, 키보드 단축키
  - 다크/라이트 테마
```

---

## 19. 스프린트 7 회고 (Retrospective)

**기간:** Sprint 7 (Phase 3 후반)
**회고일:** 2026-02-14
**완료 항목:** S7-1~S7-7 (7/7 = 100% 완료)

### 19.1 Sprint 7 완료 사항 점검

| # | 작업 | 커밋 | 산출물 요약 | 품질 평가 |
|---|------|------|-----------|----------|
| S7-1 | 데이터 내보내기 | `f77d439` | Export API 3종 (memories JSON, journals Markdown, 전체 백업). SettingsView "데이터 관리" 섹션. | **풀스택 완성.** 사용자 데이터 주권 확보. |
| S7-2 | 성능 최적화 | `4b75421` | 서버 TTL 캐시 (cachetools), 프론트 코드 스플리팅 (React.lazy), React.memo 적용. | **30파일, +1366줄 (Sprint 7 전체).** 캐시 인프라 견고. |
| S7-3 | 랜딩 페이지 | `1a790dd` | Hero + 기능 소개 + 기술 스택 + CTA. 라이트/다크 대응. 반응형. | **포트폴리오 첫인상 확보.** |
| S7-4 | PWA 완성 | `defc2ee` | manifest.json, SW 오프라인 폴백, 설치 프롬프트 (usePWAInstall 훅). | **Lighthouse PWA 기준 충족.** |
| S7-5 | UX 폴리싱 | `a4c6b67` | 스켈레톤 로딩, 페이지 전환 애니메이션, 마이크로 인터랙션, 다크/라이트 전환. | **사용자 체감 품질 향상.** |
| S7-6 | 보안 강화 | `def8a5e` | ErrorBoundary, rate_limit 미들웨어, CORS ALLOWED_ORIGINS, Pydantic 필드 검증. | **프로덕션 배포 전제 조건 충족.** |
| S7-7 | 리팩토링 | `47d0be1` | utils.py → utils 패키지 변환 (모듈 충돌 해소). | **기술 부채 해소.** |

### 19.2 잘한 점 (Keep)

1. **프로덕션 준비 완료**: ErrorBoundary + Rate Limit + CORS 강화 + 입력 검증으로 실제 배포 가능한 보안 수준 도달.
2. **PWA 풀 스택**: manifest + SW 오프라인 + 설치 프롬프트까지 완성. 모바일 사용자 경험 기반 확보.
3. **성능 인프라**: 서버 TTL 캐시 + 프론트 코드 스플리팅으로 데이터 증가에 대비한 확장성 확보.
4. **포트폴리오 레디**: 랜딩 페이지 + UX 폴리싱으로 "보여줄 수 있는" 수준 달성.

### 19.3 개선점 (Improve)

1. **실제 프로덕션 배포 미완**: Fly.io 백엔드 앱(`memoir-ai-backend`)은 존재하지만 suspended 상태. 프론트엔드 배포는 미설정. 환경 변수, CORS 도메인 등 프로덕션 설정 미적용.
2. **Socrates 대화 깊이 부족**: 벡터 검색 + 출처 표시까지 구현했으나, "내 기억을 아는 AI"로서의 차별화된 대화 경험은 아직 기본 수준.
3. **검색 필터 미비**: Ctrl+K 커맨드 팔레트와 MemoryView 검색이 있으나, 날짜 범위/소스 타입/태그 필터 없음.
4. **GraphView 인사이트 부재**: 시각화는 멋지지만 "그래서 뭘 알 수 있는데?"에 답하지 못함.
5. **E2E 테스트 0건**: 수동 QA에만 의존. 회귀 방지 자동화 없음.

### 19.4 Sprint 7 종합 평가

Sprint 7은 **"보여줄 수 있는 완성품"** 목표를 달성했다. 랜딩 페이지, PWA, UX 폴리싱, 보안 강화로 포트폴리오 수준의 외관을 갖추었다. 그러나 **실제 프로덕션 배포**와 **핵심 차별화 심화**(Socrates 대화 품질, GraphView 인사이트)는 Sprint 8에서 해결해야 할 과제로 남았다.

---


---

## 20. Sprint 8~12 확장 로드맵 개요

### 20.1 기존 Sprint 8 계획 폐기 사유

Sprint 1~7 완료 후, 파운더 + PM + UI/UX 전문가 + 기능 깊이 전문가 합동 리뷰 결과, 기존 Sprint 8(18일, 배포 우선) 계획은 다음 이유로 폐기한다:

1. **기능 깊이 부족**: Sprint 7까지 기능 범위 9.5/10이지만, 기능 깊이는 8.5/10에 불과. 배포보다 깊이를 먼저 끌어올려야 함.
2. **UX 완성도 미달**: 전문가 Chrome 실사용 테스트에서 6개 심각 UX 결함 발견 (저널 메모리 클릭 무반응, 그래프 노드 불가독, 대시보드 허브 역할 실패 등).
3. **"10/10 전체 달성" 필요**: 파운더 기준 9.5/9.0은 배포 불가. 기능 깊이, UX 완성도, PMF 준비도 모두 10/10이 되어야 함.
4. **배포 시점 변경**: 기능이 완성된 상태에서 배포해야 의미 있는 피드백 수집 가능. Sprint 11과 12 사이로 이동.

### 20.2 전문가 분석 기반 문서

Sprint 8~12 계획은 다음 3명의 전문가 분석을 통합하여 수립되었다:

| 전문가 | 산출물 | 핵심 발견 |
|--------|--------|-----------|
| **PM** | `SPRINT_8_12_ROADMAP.md` | 50일 5개 스프린트 로드맵. 배포를 Sprint 11로 이동. 모든 항목 10/10 달성 전략. |
| **UI/UX 전문가** | `DESIGN_SPEC_V2.md` | 디자인 일관성 규칙(border-radius/typography/spacing/button 통일), 5개 화면별 구체적 레이아웃/인터랙션/CSS 스펙, 마이크로 인터랙션, AI 패턴, 접근성. |
| **기능 깊이 전문가** | (인라인 분석) | 33개 개선 항목. 핵심: Curator 한국어 1줄 수정, 프론트에 노출 안 된 4개 대화 모드, 미사용 인지 왜곡 감지, briefing connection_hint 미구현. |

### 20.3 기능 깊이 전문가 핵심 발견 사항

| # | 발견 | 위치 | 영향 | 해결 Sprint |
|---|------|------|------|:----------:|
| D-1 | `CURATOR_SYSTEM_PROMPT`가 영어 요약 생성 | `curator_node.py` | 한국어 서비스에서 영어 요약 잔존 | 8 |
| D-2 | Socrates 4개 모드(insight/counter/summary/evening) 프론트 미노출 | `chat.py` + `ChatView.tsx` | 대화 차별화 기능 사장 | 8 |
| D-3 | `detect_cognitive_distortions` 존재하나 라우터 미연결 | `journal_service.py` | 저널 AI 깊이 미활용 | 9 |
| D-4 | briefing `connection_hint` 항상 None 반환 | `briefing_router.py` | 대시보드 연결 발견 미동작 | 10 |
| D-5 | GraphView 노드 min size 1.5, 엣지 opacity 0.12 | `GraphView.tsx` | 가독성 파괴 | 8 |
| D-6 | MemoryBlockNode 인라인 참조 Tiptap 확장 존재하나 진입점 부재 | `MemoryBlockNode.tsx` | 저널↔메모리 인라인 연결 불가 | 8 |
| D-7 | 4개 모드별 프롬프트 차별화 부족 | `prompts.py` 미분리 | 대화 품질 한계 | 9 |

### 20.4 참조 문서 안내

Sprint 8~12 상세 계획의 전체 내용은 아래 이어지는 섹션에 기술한다. 화면별 구체적 CSS/레이아웃/인터랙션 스펙은 `DESIGN_SPEC_V2.md`를 참조한다.


---



---

## 21. 전체 전략: "넓고 얕은" → "넓고 깊은"

### 21.1 파운더 피드백 핵심 진단

Sprint 1~7이 달성한 것은 **기능 범위 9.5/10**이다. 하지만 실사용 테스트와 UI/UX 전문가 리뷰에서 드러난 핵심 문제는 **기능 깊이**와 **UX 완성도**에 있다.

| 영역 | 현재 문제 | 심각도 |
|------|----------|:------:|
| **대시보드** | 허브 역할 실패, 히트맵 가독성 부재, AI 인사이트 없음 | 상 |
| **채팅** | ChatGPT와 시각적/경험적 차별화 없음 | 상 |
| **기억** | 카드 정보 밀도 부족, 영어 요약 잔존 | 상 |
| **저널** | 3-panel 구조 미구현, 메모리 카드 클릭 무반응, 인라인 참조 불가, AI 분석 위치 부적절, 자동 저장 미동작 | 상 |
| **그래프** | 노드 너무 작음, 엣지 안 보임, 라벨 읽기 어려움 | 상 |
| **메모리 요약** | 영어 요약 잔존 (한국어 서비스인데) | 중 |

### 21.2 Sprint 8~12 차별화 전략

Sprint 8~12는 **"새 기능 추가"가 아니라 "기존 기능을 10/10으로 끌어올리는"** 구간이다.

| Sprint | 테마 | 핵심 목표 |
|:------:|------|----------|
| **8** | UX 기반 재정비 + Socrates 차별화 시작 | 전 화면 UX 결함 수정 + Socrates 대화 품질 1차 강화 |
| **9** | Socrates 대화 완성 + 저널 심화 | "내 기억을 아는 AI" 체감 + 저널 3-panel 완전 동작 |
| **10** | 지식 그래프 인사이트 + 대시보드 재설계 | "내 지식 지도" 체감 + 허브로서의 대시보드 |
| **11** | 관리 체계 완성 + 프로덕션 배포 | 고급 검색, 중복 감지, 리포트 + 배포 |
| **12** | 배포 안정화 + E2E + 데모 + 포트폴리오 | 최종 마무리 |

### 21.3 "10/10 달성"의 정의

| 평가 항목 | 10/10의 의미 |
|-----------|-------------|
| 기능 범위 | 경쟁 제품(Notion, Obsidian) 대비 차별화된 기능이 3개 이상 존재하고, 빠진 핵심 기능이 없음 |
| 기능 깊이 | 각 핵심 기능(Chat, Memory, Journal, Graph, Dashboard)이 "이것 하나만으로도 쓸 가치가 있다"는 수준 |
| UX 완성도 | 모든 화면에서 빈 상태, 로딩, 에러, 전환, 마이크로 인터랙션이 완벽. 디자인 불일치 0건 |
| 코드 품질 | E2E 테스트 존재, CI/CD 동작, 기술 부채 0건, 프로덕션 보안 완비 |
| PMF 준비도 | 파운더가 매일 사용 + 지인 3명이 주 3회 이상 접속 + 데모 모드로 포트폴리오 방문자 체험 가능 |

---

## 22. Sprint 8: UX 기반 재정비 + Socrates 차별화 시작 (~10일)

**테마:** "기본기를 완벽하게" — 전 화면 UX 결함 수정 + Socrates 1차 강화

**전략적 배경:**

배포보다 기능 완성을 먼저 하기로 했다. Sprint 7까지 쌓인 UX 결함들을 먼저 해결하지 않으면, 이후 Sprint에서 기능을 추가해도 "얕은 느낌"이 사라지지 않는다. 동시에 Socrates 대화 품질 강화를 시작하여 가장 중요한 차별화 축에 투자를 시작한다.

```
┌─────────────────────────────────────────────────────────────────┐
│                    스프린트 8 일정 계획 (~10일)                     │
│                                                                 │
│  Track A (UX 결함 수정)              Track B (Socrates 시작)     │
│  ──────────────────────────        ──────────────────────────   │
│  Day 1-2:                           Day 3-4:                    │
│  S8-1 저널 UX 전면 수정              S8-3 Socrates 프로필 + 프롬프트│
│  (3-panel, 클릭, 인라인 참조,                                    │
│   자동저장, AI 위치 이동)           Day 5-6:                      │
│                                     S8-4 Socrates 장기 맥락      │
│  Day 3-4:                           + 피드백 시스템               │
│  S8-2 메모리/채팅/대시보드 UX                                     │
│  (카드 정보밀도, 영어요약,                                        │
│   채팅 차별화 UI, 히트맵)           Day 7-8:                      │
│                                     S8-5 그래프 시각화 기본 수정   │
│  Day 7:                                                         │
│  S8-6 Supabase 최적화                                           │
│                                                                 │
│  Day 9-10: S8-7 통합 QA                                         │
└─────────────────────────────────────────────────────────────────┘
```

---

### S8-1: 저널 UX 전면 수정 (Day 1-2) — FE + BE

**문제 (실사용 테스트에서 발견):**
1. 관련 메모리 카드 클릭 시 아무 동작 없음
2. @멘션/드래그앤드롭으로 에디터에 메모리 삽입 불가
3. AI 분석(AIPanel)이 에디터 아래에 위치해 글쓰기 중 참조 불가
4. 자동 저장이 동작하지 않음 (localStorage 저장은 되나 서버 저장 미동작)
5. 관련 메모리 요약이 영어로 표시
6. 3-panel 구조 미구현 (에디터 + AI + 메모리가 제대로 분리되지 않음)

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | MemorySidebar 카드 클릭 동작 | MemoryCard에 `onClick` 핸들러 추가: 클릭 시 MemoryDetailModal 열림. 카드에 hover 커서 `pointer` + 미세 lift 효과. |
| FE | @멘션 방식 인라인 참조 | Tiptap `Mention` 확장 활용: 에디터에서 `@` 입력 시 메모리 검색 드롭다운. 선택 시 메모리 참조 블록(제목 + 소스 아이콘) 인라인 삽입. 기존 `onInsertMemory`를 @멘션 방식으로 전환. |
| FE | AI 패널 위치 이동 | 에디터 아래에서 **에디터 우측 패널**로 이동. 3-panel 레이아웃 구현: [메모리 사이드바 | 에디터 | AI 패널]. 1024px 이하에서는 AI 패널을 에디터 상단 접이식으로 전환. |
| FE | 서버 자동 저장 수정 | localStorage 저장 후 디바운스 5초로 서버 `saveJournal()` 자동 호출. 저장 성공 시 "저장됨" 상태 표시 (헤더에 작은 체크 아이콘). 저장 실패 시 재시도 로직 + 토스트. |
| BE | 관련 메모리 요약 한국어화 | Librarian 에이전트의 요약 생성 프롬프트에 "반드시 한국어로 요약하세요" 지시 추가. 기존 영어 요약 메모리에 대한 일괄 재요약 스크립트 (선택적 마이그레이션). |
| FE | 3-panel 레이아웃 CSS 재설계 | `.journal-view` 를 `grid-template-columns: 280px 1fr 300px`로 재설계. 메모리 사이드바(좌), 에디터(중앙), AI 패널(우). 반응형: 1024px 이하에서 사이드바/AI 패널 접기. |

**체크포인트:**
- [ ] 관련 메모리 카드 클릭 → MemoryDetailModal 열림
- [ ] 에디터에서 `@` 입력 → 메모리 검색 → 선택 → 인라인 블록 삽입
- [ ] AI 패널이 에디터 우측에 위치 (3-panel 레이아웃)
- [ ] 텍스트 입력 후 5초 대기 → 서버 자동 저장 + "저장됨" 표시
- [ ] 관련 메모리 요약이 한국어로 표시
- [ ] 1024px 이하에서 패널 접기/펼치기 정상

---

### S8-2: 메모리/채팅/대시보드 UX 수정 (Day 3-4) — FE

**문제 (UI/UX 전문가 리뷰):**
1. 메모리 카드 정보 밀도 부족 (제목만 보임, 소스/날짜/태그 부재)
2. 메모리 요약이 영어로 표시되는 경우 있음
3. 채팅이 ChatGPT와 시각적 차별화 없음
4. 대시보드 히트맵 가독성 부재 + AI 인사이트 없음

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | 메모리 카드 정보 밀도 강화 | 카드에 표시: 제목(1줄) + 요약(2줄 truncate) + 소스 타입 아이콘 + 날짜(상대 시간) + 태그 칩(최대 3개). 카드 레이아웃을 2-column 그리드로. hover 시 전체 요약 툴팁. |
| FE | 채팅 차별화 UI | (1) AI 응답에 "기억을 참조했습니다" 인디케이터 강화 (배경색 차이 + 아이콘). (2) 빈 채팅 상태에서 "Socrates는 당신의 기억을 알고 있습니다" 히어로 텍스트 + 추천 질문 카드 3개 (메모리 기반 동적 생성). (3) 사이드바에 최근 대화 세션 미리보기 (제목 + 마지막 메시지 1줄). |
| FE | 대시보드 히트맵 개선 | 히트맵 셀에 hover 시 날짜 + 활동 수 툴팁. 색상 스케일 범례 추가 (0건 → N건). 오늘 날짜 하이라이트. 히트맵 아래에 "이번 달 활동 요약" 한 줄 텍스트. |
| FE | 대시보드 브리핑 카드 재설계 | 현재 브리핑이 단순 텍스트 나열. 카드별 아이콘 + 색상 구분 + CTA 버튼 강화. "오늘의 질문" 카드를 가장 눈에 띄게. 브리핑 없는 상태 (메모리 0개)에서 온보딩 유도 카드. |

**체크포인트:**
- [ ] 메모리 카드에 소스 아이콘, 날짜, 태그 칩 표시
- [ ] 빈 채팅에서 "Socrates는 당신의 기억을 알고 있습니다" + 추천 질문
- [ ] 히트맵 hover → 날짜 + 활동 수 툴팁
- [ ] 대시보드 브리핑 카드가 시각적으로 구분됨

---

### S8-3: Socrates 사용자 프로필 + 프롬프트 고도화 (Day 3-4) — BE

**문제:** Socrates가 벡터 검색 결과를 컨텍스트에 넣는 "검색 대리" 수준. "내 기억을 아는 AI 파트너"와의 경험 격차가 큼.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | `user_profile_service.py` 신규 | 메모리 태그 빈도 상위 5개 + 최근 2주 저널 키워드 추출 → 사용자 관심사 프로필 자동 생성. 시스템 프롬프트에 동적 주입: "이 사용자는 {관심사1}, {관심사2}, {관심사3}에 관심이 많습니다. 최근에는 {최근 주제}에 대해 많이 탐구하고 있습니다." 24시간 TTL 캐시. |
| BE | 프롬프트 엔지니어링 v2 | Socrates 시스템 프롬프트 전면 개선: (1) **비판적 질문**: "이 관점에 대해 다른 시각은 없을까요?", (2) **연결 제안**: "이 기억이 저번 주에 저장한 {X}와 관련있는 것 같은데, 어떻게 생각하세요?", (3) **패턴 발견**: "최근 {주제}에 대한 기억이 많이 쌓이고 있네요. 특별한 이유가 있나요?" 프롬프트를 `prompts.py` 상수 파일로 분리하여 버전 관리. |
| BE | 응답 스타일 차별화 | 메모리 참조 응답 시: 단순 요약이 아니라 "저장하신 기억에 따르면..." 스타일로 인격화. 참조 없는 일반 대화에서도 사용자 프로필 기반 맞춤 톤. |

**체크포인트:**
- [ ] "내가 최근에 관심 있는 주제가 뭐야?" → 실제 메모리 태그 기반 관심사 답변
- [ ] 메모리 참조 시 비판적 질문 또는 연결 제안이 자연스럽게 포함
- [ ] 프롬프트가 `prompts.py`로 분리되어 버전 관리 가능

---

### S8-4: Socrates 장기 맥락 + 피드백 시스템 (Day 5-6) — 풀스택

**문제:** 세션 간 맥락이 유지되지 않아 매번 백지에서 시작하는 느낌. 대화 품질 개선 루프가 없음.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | 세션 요약 자동 생성 | 세션 종료(마지막 메시지 후 30분 비활동) 또는 새 세션 시작 시, 이전 세션의 대화를 LLM으로 3줄 요약 자동 생성. `chat_sessions` 테이블에 `summary` 필드 추가. gpt-4o-mini 사용 (비용 최소). |
| BE | 이전 세션 요약 컨텍스트 주입 | 새 세션의 첫 메시지 시, 최근 3개 세션 요약을 시스템 프롬프트에 포함: "이전 대화 요약: [세션1 요약], [세션2 요약], [세션3 요약]". "지난번에 AI 윤리에 대해 이야기했었죠" 수준의 장기 기억 효과. |
| BE | 피드백 API | `POST /api/v1/chat/feedback` — message_id, rating (good/bad), comment (선택). `chat_feedback` 테이블에 저장. |
| FE | 피드백 UI | AI 응답 메시지 하단에 작은 "도움이 됐어요 / 아쉬워요" 아이콘 버튼 (thumbs up/down). 클릭 시 버튼 상태 변경(색상) + API 호출. 과도한 UI 면적 차지하지 않도록 아이콘만. |

**체크포인트:**
- [ ] 새 세션에서 "지난번에 뭐 얘기했었지?" → 이전 세션 내용 기반 답변
- [ ] 피드백 버튼 클릭 → 서버에 기록
- [ ] 세션 3개 이상 축적 후 장기 맥락 효과 체감

---

### S8-5: 그래프 시각화 기본 수정 (Day 7-8) — FE

**문제 (UI/UX 전문가):** 노드 너무 작음, 엣지 안 보임, 라벨 읽기 어려움. "예쁜 데모"는 되지만 실제로 정보를 얻기 어려움.

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | 노드 크기 증가 | `Math.max(1.5, Math.sqrt(val) * 1.5)` → `Math.max(3, Math.sqrt(val) * 2.5)` 로 기본 크기 2배. 연결 수(degree)에 비례하여 중요 노드를 더 크게. |
| FE | 엣지 시각성 강화 | 엣지 width를 `0.5` → `1.5`로 증가. 엣지 색상을 연한 회색에서 소스/타겟 노드 색상 블렌딩으로. 호버 시 연결된 엣지를 강조 색상 + 두꺼운 선(3px)으로. |
| FE | 라벨 가독성 개선 | `textHeight`를 `Math.max(1.2, size * 0.5)` → `Math.max(2.0, size * 0.7)`로 증가. 라벨 배경에 더 뚜렷한 대비색 적용. 긴 라벨 말줄임 24자 → 30자로 확대. 선택된 노드의 라벨은 볼드 + 크기 1.5배. |
| FE | 초기 줌 레벨 조정 | 그래프 로딩 후 전체 노드가 화면에 적절히 들어오는 줌 레벨로 자동 조정. `fgRef.current.zoomToFit(400)` 호출. 노드 간 간격 증가 (`d3AlphaDecay` / `d3VelocityDecay` 조정). |
| FE | 정보 패널 재설계 | 선택 노드 정보 패널: 노드 타입 + 이름 + 연결 수 + 관련 메모리 목록(최대 5개). 관련 메모리 클릭 → MemoryDetailModal. 패널 위치를 하단에서 우측 사이드로 이동 (그래프 영역 최대화). |

**체크포인트:**
- [ ] 노드 라벨이 줌 없이도 읽을 수 있는 크기
- [ ] 엣지(선)가 명확하게 보임
- [ ] 노드 호버 시 연결 관계가 시각적으로 강조
- [ ] 전체 그래프 구조를 한눈에 파악 가능
- [ ] 정보 패널에서 관련 메모리 클릭 → 상세 모달

---

### S8-6: Supabase 스키마 최적화 + 프로덕션 준비 (Day 7) — BE/인프라

**문제:** 프로덕션 데이터 기준으로 인덱스, RLS, 무료 티어 한계를 미리 점검하지 않으면 Sprint 9~11에서 예상치 못한 장애 발생.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | 인덱스 점검 | 벡터 검색(pgvector)에 IVFFlat 또는 HNSW 인덱스 확인. `memories` 테이블의 `user_id`, `created_at`, `source_type`, `tags` 컬럼에 B-tree 인덱스 추가 (고급 검색 필터 대비). `chat_sessions`의 `user_id + created_at` 복합 인덱스. |
| BE | RLS 정책 재확인 | 모든 테이블에 `user_id = auth.uid()` RLS 정책이 적용되어 있는지 전수 조사. 누락된 테이블에 즉시 적용. 특히 `chat_feedback`, `journal_memory_links` 등 Sprint 6 이후 추가 테이블. |
| 인프라 | 무료 티어 한계 문서화 | Supabase Free: 500MB DB, 1GB 스토리지, 50,000 MAU. Fly.io Free: 3 shared-cpu VMs, 256MB RAM. 현재 사용량 확인 + 한계 도달 시 업그레이드 플랜 정리. |
| BE | 세션 요약용 DB 마이그레이션 | `chat_sessions` 테이블에 `summary TEXT` 필드 추가. `chat_feedback` 테이블 생성: id, user_id, session_id, message_id, rating, comment, created_at. |

**체크포인트:**
- [ ] 벡터 검색 인덱스 존재 확인
- [ ] 모든 테이블 RLS 정책 적용 확인
- [ ] 무료 티어 사용량 확인 + 한계 문서화
- [ ] chat_feedback 테이블 마이그레이션 완료

---

### S8-7: Sprint 8 통합 QA (Day 9-10)

**통합 QA 체크리스트:**

저널 UX:
- [x] 관련 메모리 카드 클릭 → 상세 모달
- [x] @멘션으로 메모리 인라인 삽입
- [x] 3-panel 레이아웃 (메모리 | 에디터 | AI)
- [x] 서버 자동 저장 + "저장됨" 표시
- [x] 관련 메모리 요약 한국어 표시
- [x] 1024px 이하 반응형 (코드 검증: JournalView.css @media 1024px + 767px)

메모리/채팅/대시보드:
- [x] 메모리 카드에 소스/날짜/태그 표시
- [x] 채팅 빈 상태 차별화 UI
- [x] 히트맵 hover 툴팁 ("2026-02-12 · 1개 활동" 확인)
- [x] 브리핑 카드 시각적 구분

Socrates:
- [x] 사용자 프로필 기반 관심사 답변
- [x] 비판적 질문/연결 제안 포함
- [x] 이전 세션 요약 기반 장기 맥락
- [x] 피드백 thumbs up/down 동작

그래프:
- [x] 노드 라벨 가독성
- [x] 엣지 시각성
- [x] 정보 패널 관련 메모리 클릭 (검색 "Supabase" → info panel + 관련 메모리 2개)

기존 기능 회귀:
- [x] Chat SSE 스트리밍
- [x] 메모리 CRUD + 편집 + 일괄 관리
- [x] 저널 작성/히스토리
- [x] 글로벌 검색 Ctrl+K ("Deno" 검색 → 메모리 결과 즉시 표시)
- [x] 넛지 알림 (코드 검증: 스케줄러 + push API 존재)

---

### Sprint 8 의존성 그래프

```
S8-1 (저널 UX) ──────────────────── Day 1-2, 독립
S8-2 (메모리/채팅/대시보드 UX) ──── Day 3-4, 독립
S8-3 (Socrates 프로필+프롬프트) ──── Day 3-4, 독립

S8-3 ──> S8-4 (장기 맥락+피드백)     Day 5-6

S8-5 (그래프 시각화) ─────────────── Day 7-8, 독립
S8-6 (Supabase 최적화) ──────────── Day 7, 독립

전체 ──> S8-7 (통합 QA)              Day 9-10
```

---

### Sprint 8 진행 체크리스트

- [x] S8-1: 저널 UX 전면 수정 (3-panel, 클릭, @멘션, 자동저장, AI위치, 한국어 요약) (`94d4706`)
- [x] S8-2: 메모리/채팅/대시보드 UX (카드 정보밀도, 채팅 차별화, 히트맵 개선) (`94d4706`)
- [x] S8-3: Socrates 프로필 + 프롬프트 고도화 (`94d4706`)
- [x] S8-4: Socrates 장기 맥락 + 피드백 (`94d4706`)
- [x] S8-5: 그래프 시각화 기본 수정 (노드/엣지/라벨 가독성) (`94d4706`)
- [x] S8-6: Supabase 최적화 + DB 마이그레이션 (`389ea5f`)
- [x] S8-7: 통합 QA (정적 검증 + 브라우저 QA 20개 항목 전항 PASS)

---

## 23. Sprint 9: Socrates 대화 완성 + 저널 심화 (~10일)

**테마:** "내 기억을 아는 AI 파트너 완성" — Socrates 대화 10/10 + 저널 10/10

**전략적 배경:**

Sprint 8에서 Socrates 1차 강화(프로필, 프롬프트, 장기 맥락)와 저널 UX 기본 수정을 했다. Sprint 9는 이 두 핵심 영역의 **깊이를 10/10으로 끌어올리는** 스프린트다. Socrates가 "진짜 내 기억을 아는 AI"로 느껴지려면, 단순 프로필 주입을 넘어서 **대화 중 실시간으로 기억을 연결하고**, **사용자의 사고를 확장하는** 경험이 필요하다. 저널은 @멘션 기반 참조를 넘어서 **AI가 능동적으로 회고를 돕는** 경험이 필요하다.

```
┌─────────────────────────────────────────────────────────────────┐
│                    스프린트 9 일정 계획 (~10일)                     │
│                                                                 │
│  Track A (Socrates 완성)            Track B (저널 심화)           │
│  ──────────────────────────        ──────────────────────────   │
│  Day 1-2:                           Day 1-2:                    │
│  S9-1 대화 중 실시간 연결 제안       S9-3 저널 AI 능동 회고       │
│                                                                 │
│  Day 3-4:                           Day 3-4:                    │
│  S9-2 대화 품질 튜닝 + 검증          S9-4 저널-메모리 플로우 완성 │
│                                                                 │
│  Day 5-6:                                                       │
│  S9-5 채팅 UX 완성도 (마이크로 인터랙션 + 빈 상태 + 전환)         │
│                                                                 │
│  Day 7-8:                                                       │
│  S9-6 메모리 요약 한국어 일괄 전환 + 요약 품질 강화               │
│                                                                 │
│  Day 9-10: S9-7 통합 QA + Socrates 10개 시나리오 검증            │
└─────────────────────────────────────────────────────────────────┘
```

---

### S9-1: 대화 중 실시간 연결 제안 (Day 1-2) — BE

**문제:** Sprint 8에서 프로필+프롬프트+장기맥락을 도입했지만, 대화 **중에** 실시간으로 "이거 저번에 저장한 것과 연결되는데요"를 제안하지 못함. 이것이 Memoir Socrates의 궁극적 차별화 포인트.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | 대화 중 연결 감지 로직 | Socrates 응답 생성 시, (1) 현재 대화 주제 키워드 추출, (2) 해당 키워드로 벡터 검색, (3) **현재 대화에서 직접 질문하지 않았지만 관련된 메모리** 발견 시 → "참고로, 2주 전에 저장하신 '{메모리 제목}'도 이 주제와 관련이 있을 수 있어요. 궁금하시면 말씀해주세요." 형태로 응답 말미에 자연스럽게 삽입. 빈도 제한: 3턴에 1회 이하. |
| BE | 연결 품질 필터 | 유사도 0.80~0.92 범위의 메모리만 연결 제안 (0.92 이상은 이미 참조에 포함될 가능성 높음, 0.80 미만은 관련성 낮음). 이미 참조된 메모리는 중복 제안하지 않음. 최근 24시간 이내 저장된 메모리 우선. |

**체크포인트:**
- [ ] AI 관련 질문 → 응답 중 "관련 있을 수 있는 기억" 자연스럽게 제안
- [ ] 3턴 연속 제안하지 않음 (빈도 제한)
- [ ] 이미 참조한 메모리 중복 제안 없음

---

### S9-2: 대화 품질 튜닝 + 10개 시나리오 검증 (Day 3-4) — BE

**문제:** 프롬프트 개선의 효과를 체계적으로 검증하지 않으면 "좋아진 것 같은데 정확히 뭐가 좋아졌는지 모르겠음" 상태가 됨.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | 10개 시나리오 테스트 셋 작성 | (1) "내 관심사가 뭐야?" (프로필 기반), (2) "저번에 저장한 AI 글 요약해줘" (명시적 검색), (3) "요즘 뭐에 관심이 많아?" (패턴 발견), (4) "지난번 대화 이어서 하자" (장기 맥락), (5) "이 기사에 대해 어떻게 생각해?" (비판적 질문), (6) 일반 대화 (메모리 무관), (7) 모호한 질문 (의도 분류 테스트), (8) 복합 질문 (검색+의견), (9) 감정적 대화 (공감 능력), (10) 후속 질문 체인 (맥락 유지). |
| BE | 프롬프트 반복 튜닝 | 각 시나리오에서 "기존 ChatGPT와 다르다"고 느끼는 응답 비율이 **80% 이상**이 될 때까지 프롬프트 반복 수정. 특히 (5) 비판적 질문, (9) 공감 능력에서 차별화 집중. |
| BE | 검색 컨텍스트 양 최적화 | top_k를 3→5로 증가하여 더 풍부한 컨텍스트 제공. 단, 토큰 비용 증가 모니터링. 컨텍스트 삽입 형식 개선: 각 메모리를 "--- 기억 #{N} ---" 블록으로 구분하여 LLM이 더 잘 구별하도록. |

**체크포인트:**
- [ ] 10개 시나리오 중 8개 이상에서 "ChatGPT와 다르다" 체감
- [ ] 비판적 질문이 자연스럽게 포함되는 비율 70%+
- [ ] 연결 제안이 실제로 관련성 있는 비율 80%+

---

### S9-3: 저널 AI 능동 회고 시스템 (Day 1-2) — 풀스택

**문제:** AI 패널이 수동 버튼("하루 정리", "세션 기반 초안")만 제공. 에디터에 글을 쓰기 시작하면 AI가 자동으로 회고 질문을 던지는 능동적 경험이 필요.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | 실시간 회고 질문 API 개선 | 기존 `review-questions` API를 확장: 에디터 내용(현재 작성 중인 글)을 입력으로 받아 **맥락에 맞는** 후속 질문 생성. "이 부분을 좀 더 자세히 적어볼까요?", "이 경험에서 얻은 교훈은 무엇인가요?", "비슷한 경험이 이전에도 있었나요?" |
| FE | AI 패널 능동 모드 | 에디터 내용이 100자 이상일 때 자동으로 AI 패널에 회고 질문 표시 (디바운스 5초). 질문 카드 클릭 → 에디터에 질문을 프롬프트로 삽입 ("## 오늘의 교훈\n"). "더 많은 질문 보기" 버튼으로 추가 질문 요청. |
| FE | 회고 템플릿 선택 | AI 패널 상단에 템플릿 드롭다운: "자유 형식", "오늘의 TIL", "이번 주 회고", "프로젝트 회고". 템플릿 선택 → 에디터에 구조 삽입 (## 제목, - 항목 등). 각 템플릿에 맞는 AI 질문 자동 생성. |

**체크포인트:**
- [ ] 글 100자 이상 작성 시 → AI 패널에 맥락 맞는 회고 질문 자동 표시
- [ ] 질문 카드 클릭 → 에디터에 프롬프트 삽입
- [ ] 4종 회고 템플릿 선택 → 에디터에 구조 삽입

---

### S9-4: 저널-메모리 연결 플로우 완성 (Day 3-4) — 풀스택

**문제:** Sprint 8에서 @멘션 삽입과 카드 클릭을 구현했지만, 저널↔메모리 **양방향 연결의 순환 루프**가 완전하지 않음.

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | 저널 저장 시 자동 링크 강화 | 에디터 내용에서 @멘션된 메모리 ID를 자동 추출 → `journal_memory_links` 자동 생성. 기존 자동 감지(content 기반)와 @멘션(명시적) 모두 반영. 중복 방지. |
| FE | MemoryDetailModal "관련 저널" 강화 | 관련 저널 섹션에 날짜 + 첫 줄 미리보기 + 연결 유형(자동/수동) 표시. 클릭 → JournalView 해당 날짜로 이동. 연결 없으면 "이 기억에 대해 저널을 써보는 건 어떨까요?" CTA → JournalView로 이동 + 메모리 참조 프리필. |
| FE | 메모리 사이드바 정보량 강화 | 관련 메모리 카드에 요약(2줄) + 소스 타입 + 유사도(관련 탭) 표시. 카드 하단에 "인용하기" 작은 버튼 (기존 onInsertMemory) + "상세 보기" 버튼 분리. |

**체크포인트:**
- [ ] 저널 저장 후 → 참조된 메모리의 상세 모달에서 "관련 저널" 즉시 표시
- [ ] "관련 저널" 클릭 → 해당 날짜 저널 이동
- [ ] 연결 없는 메모리에서 "저널 써보기" CTA → 프리필된 JournalView

---

### S9-5: 채팅 UX 완성도 (Day 5-6) — FE

**문제:** 채팅의 마이크로 인터랙션, 로딩 상태, 빈 상태 처리가 미완. ChatGPT 수준의 폴리싱이 필요.

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | SSE 타이핑 인디케이터 | AI 응답 수신 중: "Socrates가 생각하고 있습니다..." 애니메이션 (3점 bouncing dots). 응답 시작 후: 토큰 단위 텍스트 출현 (기존 동작 유지). |
| FE | 메시지 전환 애니메이션 | 새 메시지 등장 시 fade-in + slide-up 애니메이션 (200ms). 자동 스크롤이 마지막 메시지를 보여주되, 사용자가 위로 스크롤한 상태면 스크롤하지 않음. |
| FE | 참조 메모리 UI 개선 | 참조 메모리 접이식 섹션: 기본 접힌 상태에서 작은 배지 "N개 기억 참조". 펼치면 카드형으로 표시 (제목 + 소스 아이콘 + 날짜). 카드 클릭 → MemoryDetailModal. |
| FE | 사이드바 세션 목록 개선 | 세션 제목(자동 생성된) + 마지막 메시지 1줄 미리보기 + 시간. 오늘/이번 주/이전 그룹핑. |
| FE | 빈 채팅 경험 완성 | 세션 없는 상태: "Socrates" 로고 + "당신의 기억을 알고 있는 AI" 서브텍스트. 메모리 기반 추천 질문 3개 (briefing API 활용). 추천 질문 클릭 → 자동 전송. "혹은 자유롭게 물어보세요" 안내. |

**체크포인트:**
- [ ] AI 응답 중 타이핑 인디케이터 표시
- [ ] 메시지 등장 시 부드러운 애니메이션
- [ ] 참조 메모리 접기/펼치기 + 카드 클릭 → 상세 모달
- [ ] 빈 채팅에서 추천 질문 3개 + 클릭 → 자동 전송

---

### S9-6: 메모리 요약 한국어 일괄 전환 + 요약 품질 강화 (Day 7-8) — BE

**문제:** 기존 메모리 중 영어 요약이 다수 잔존. 새 메모리도 Librarian 프롬프트에 따라 영어로 요약될 수 있음. 한국어 서비스에서 영어 요약은 UX 파괴.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | Librarian 프롬프트 한국어 강제 | 메모리 요약 생성 프롬프트에 "반드시 한국어로 요약하세요. 원본이 영어라도 한국어로 요약하세요." 명시. 태그도 한국어 우선 (기술 용어는 영어 허용). |
| BE | 기존 메모리 일괄 재요약 스크립트 | `scripts/migrate_summaries.py` 신규: user_id 기반으로 기존 메모리 순회 → 영어 요약 감지 (문자 비율 체크) → LLM 재요약 호출 → DB 업데이트. 배치 처리 (10개씩, rate limit 준수). 실행 전 확인 프롬프트. |
| BE | 요약 품질 강화 | 요약 길이: 1줄 → 2~3줄로 증가 (카드 정보 밀도 향상). 요약에 핵심 인사이트 1개 포함: "이 글의 핵심은 {주장}이며, {근거}를 들어 설명합니다" 형태. |

**체크포인트:**
- [ ] 새 메모리 저장 → 한국어 요약 생성
- [ ] 기존 영어 요약 메모리 → 일괄 재요약 완료
- [ ] 요약이 2~3줄로 충분한 정보 밀도 제공

---

### S9-7: Sprint 9 통합 QA + Socrates 10개 시나리오 최종 검증 (Day 9-10)

**통합 QA 체크리스트:**

Socrates 대화 완성:
- [ ] 10개 시나리오 중 8개+ "ChatGPT와 다르다" 체감
- [ ] 대화 중 연결 제안 자연스러움
- [ ] 장기 맥락 (이전 세션 내용 반영)
- [ ] 피드백 수집 동작

저널 심화:
- [ ] 3-panel 레이아웃 완전 동작
- [ ] @멘션 인라인 참조
- [ ] AI 능동 회고 질문
- [ ] 4종 템플릿
- [ ] 자동 저장 서버 반영
- [ ] 저널↔메모리 양방향 연결 순환

채팅 UX:
- [ ] 타이핑 인디케이터
- [ ] 메시지 애니메이션
- [ ] 참조 메모리 접기/펼치기
- [ ] 빈 채팅 추천 질문

메모리 요약:
- [ ] 전체 메모리 한국어 요약
- [ ] 요약 2~3줄 정보 밀도

---

### Sprint 9 진행 체크리스트

- [x] S9-1: 대화 중 실시간 연결 제안
- [x] S9-2: 대화 품질 튜닝 + 10개 시나리오 검증
- [x] S9-3: 저널 AI 능동 회고 시스템
- [x] S9-4: 저널-메모리 연결 플로우 완성
- [x] S9-5: 채팅 UX 완성도
- [x] S9-6: 메모리 요약 한국어 일괄 전환 + 품질 강화
- [x] S9-7: 통합 QA + Socrates 시나리오 검증

---

## 24. Sprint 10: 지식 그래프 인사이트 + 대시보드 재설계 (~10일)

**테마:** "내 지식 지도를 읽다 + 매일 돌아오는 허브" — GraphView 인사이트 10/10 + Dashboard 10/10

**전략적 배경:**

Sprint 8~9에서 Socrates와 저널의 깊이를 10/10으로 끌어올렸다. Sprint 10은 나머지 두 핵심 영역을 공략한다. GraphView는 Sprint 8에서 시각성을 개선했지만, "그래서 뭘 알 수 있는데?"에 답하지 못한다. 대시보드는 "허브 역할 실패"라는 진단을 받았다. 이 두 영역은 **"사용자를 매일 돌아오게 하는 힘"**과 직결된다.

```
┌─────────────────────────────────────────────────────────────────┐
│                    스프린트 10 일정 계획 (~10일)                    │
│                                                                 │
│  Track A (그래프 인사이트)           Track B (대시보드 재설계)     │
│  ──────────────────────────        ──────────────────────────   │
│  Day 1-2:                           Day 1-2:                    │
│  S10-1 인사이트 분석 엔진            S10-3 대시보드 허브 재설계    │
│                                                                 │
│  Day 3-4:                           Day 5-6:                    │
│  S10-2 인사이트 패널 UI             S10-4 대시보드 AI 인사이트    │
│  + 클러스터 시각화                                               │
│                                                                 │
│  Day 5-6:                                                       │
│  S10-5 그래프 → 다른 뷰 연결                                     │
│                                                                 │
│  Day 7-8:                                                       │
│  S10-6 전체 UX 디테일 폴리싱 (빈 상태, 로딩, 전환, 마이크로)     │
│                                                                 │
│  Day 9-10: S10-7 통합 QA                                        │
└─────────────────────────────────────────────────────────────────┘
```

---

### S10-1: 그래프 인사이트 분석 엔진 (Day 1-2) — BE

**문제:** GraphView가 "예쁜 3D 시각화" 이상의 가치를 제공하지 못함.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | `GET /api/v1/graph/insights` API | 4가지 인사이트 분석: (1) **클러스터 감지**: KuzuDB 그래프에서 연결 밀도 기반 community detection. 각 클러스터의 메모리 ID + 대표 태그. (2) **관심사 트렌드**: 최근 4주간 주별 태그 빈도 변화. 상승/하락 화살표. (3) **고립 노드**: 다른 메모리와 연결 0개인 노드 목록. (4) **허브 노드**: 연결이 가장 많은 상위 5개 메모리. |
| BE | 클러스터 LLM 요약 | 각 클러스터의 메모리 제목+태그를 gpt-4o-mini에 전달하여 한 줄 요약: "AI 도구 활용법에 깊은 관심을 보이고 있습니다" 형태. 10분 TTL 캐시. |

**체크포인트:**
- [ ] 메모리 20개 이상 시 최소 2개 클러스터 감지
- [ ] 클러스터 요약이 실제 내용과 부합 (한국어)
- [ ] 트렌드에서 상승/하락 주제 식별
- [ ] 고립 노드와 허브 노드 정확히 식별

---

### S10-2: 인사이트 패널 UI + 클러스터 시각화 (Day 3-4) — FE

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | GraphView 인사이트 패널 | 우측 접이식 패널 (Sprint 8에서 이동한 정보 패널 확장). 4개 섹션: (1) 클러스터 카드 (색상+주제+메모리 수. 클릭 → 해당 노드 하이라이트), (2) 트렌드 (4주 바 차트. 상승 주제 하이라이트), (3) 고립 기억 (목록 + "연결 만들기" CTA), (4) 지식 허브 (Top 5 메모리). |
| FE | 클러스터 색상 시각화 | 같은 클러스터 노드를 동일 색상으로 그룹핑 (기존 타입별 색상에서 클러스터별 색상으로 토글 가능). 인사이트 패널에서 클러스터 선택 시 해당 노드들 줌인. |
| FE | "연결 만들기" 기능 | 고립 노드 카드의 CTA 클릭 → 해당 메모리로 벡터 검색 → 유사 메모리 목록 표시 → "연결하기" 버튼으로 수동 관계 생성 (KuzuDB에 SIMILAR_TO 엣지). |

**체크포인트:**
- [ ] 인사이트 패널에 4개 섹션 표시
- [ ] 클러스터 카드 클릭 → 해당 노드 하이라이트 + 줌인
- [ ] 고립 노드 "연결 만들기" → 유사 메모리 검색 → 연결 생성

---

### S10-3: 대시보드 허브 재설계 (Day 1-2) — FE

**문제:** "대시보드가 허브 역할 실패" — 현재 통계 나열에 불과. 사용자가 "오늘 뭐하지?"에 답을 얻지 못함.

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | 레이아웃 전면 재설계 | 상단: 오늘의 브리핑 (히어로 카드). 중단: 퀵 액션 그리드 (4개 카드: "저널 쓰기" / "기억 탐색" / "Socrates와 대화" / "지식 그래프"). 하단: 활동 통계 (스트릭 + 히트맵 + 태그 차트). 각 영역 간 시각적 구분 명확히. |
| FE | 브리핑 히어로 카드 | "좋은 저녁이에요, {닉네임}님" 인사. 오늘 수집된 기억 N개, 미회고 기억 N개, 저널 스트릭 N일. "오늘의 질문"을 가장 눈에 띄게 (큰 텍스트 + 배경색). 질문 클릭 → JournalView로 이동. |
| FE | 히트맵 가독성 완성 | 요일 라벨 (월~일) 좌측 표시. 월 라벨 상단 표시. 색상 범례 (0건→연한, N건→진한). hover 시 날짜 + 활동 수 + 종류(메모리/저널/대화) 상세 툴팁. 오늘 날짜 하이라이트(테두리). |
| FE | 퀵 액션 카드 | 각 카드: 아이콘(Lucide) + 제목 + 부제(동적). "저널 쓰기" → "오늘 아직 작성하지 않았어요" 또는 "오늘 작성 완료!". "기억 탐색" → "총 {N}개의 기억". 카드 클릭 → 해당 뷰 이동. hover 시 미세 lift. |

**체크포인트:**
- [ ] 대시보드 접속 시 "오늘 뭐하지?"에 3초 내 답 얻을 수 있음
- [ ] 브리핑 히어로 카드에 인사 + 통계 + 오늘의 질문
- [ ] 히트맵에 요일/월 라벨 + hover 툴팁 + 색상 범례
- [ ] 4개 퀵 액션 카드 클릭 → 각 뷰 이동

---

### S10-4: 대시보드 AI 인사이트 (Day 5-6) — 풀스택

**문제:** "AI 인사이트 없음" — 대시보드가 데이터만 보여주고 의미를 해석하지 않음.

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | `GET /api/v1/insights/daily` API | 오늘의 AI 인사이트 1~2개 자동 생성: (1) 최근 기억 패턴: "이번 주에는 {주제}에 집중하고 계시네요", (2) 연결 발견: "{기억A}와 {기억B}가 연결될 수 있어요", (3) 행동 제안: "3일 동안 저널을 작성하지 않았어요. 이번 주를 돌아보는 건 어떨까요?". 기존 nudge_service + graph_insight_service 로직 재활용. gpt-4o-mini. 30분 TTL 캐시. |
| FE | 인사이트 카드 UI | 브리핑 아래에 "AI가 발견한 것" 섹션. 카드형: 라이트 배경 + 아이콘 + 인사이트 텍스트 + CTA. CTA 클릭 시 관련 뷰로 이동 (저널, 메모리, 그래프). |

**체크포인트:**
- [ ] 대시보드에 AI 인사이트 카드 1~2개 표시
- [ ] 인사이트가 실제 활동과 관련성 있음
- [ ] CTA 클릭 → 관련 뷰로 이동

---

### S10-5: 그래프 → 다른 뷰 연결 강화 (Day 5-6) — FE

**문제:** 그래프가 "고립된 시각화". 다른 뷰와 연결되지 않으면 "보기만 하는" 기능에 머무름.

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | 노드 더블클릭 → 상세 모달 | Memory 타입 노드 더블클릭 → MemoryDetailModal 직접 열림 (현재는 사이드 패널만). |
| FE | 클러스터 → Socrates 대화 | 인사이트 패널의 클러스터 요약 옆 "이 주제에 대해 대화하기" 버튼. 클릭 → ChatView로 이동 + "내가 {클러스터 주제}에 대해 저장한 기억들을 정리해줘" 자동 전송. |
| FE | 고립 노드 → MemoryView 이동 | 고립 노드 카드의 "상세 보기" 클릭 → MemoryView에서 해당 메모리 하이라이트. |
| FE | 그래프에서 검색 → 필터 연동 | 그래프 검색에서 노드를 찾으면, "기억 뷰에서 보기" 링크 → MemoryView에 해당 태그/소스 필터 적용. |

**체크포인트:**
- [ ] Memory 노드 더블클릭 → 상세 모달
- [ ] 클러스터 "대화하기" → ChatView + 자동 메시지
- [ ] 그래프가 "행동을 유발하는 도구"가 되었는지 주관적 검증

---

### S10-6: 전체 UX 디테일 폴리싱 (Day 7-8) — FE

**문제:** 기능 깊이와 별개로, 빈 상태/로딩/전환/에러 처리의 **일관성**이 10/10의 핵심.

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | 빈 상태 전수 점검 | 모든 뷰의 빈 상태(데이터 0건)에 일관된 일러스트 + 안내 텍스트 + CTA 버튼. MemoryView 0개: "첫 기억을 추가해보세요" + [추가하기]. Journal 미작성: "오늘을 돌아보세요" + [시작하기]. Graph 노드 0개: "기억이 쌓이면 지식 지도가 그려집니다". |
| FE | 로딩 상태 일관성 | 모든 데이터 로딩에 스켈레톤 UI 적용 확인 (Sprint 7에서 일부 구현). GraphView 로딩: 3D 캔버스 대신 스켈레톤. DashboardView 각 섹션별 독립 스켈레톤. |
| FE | 에러 상태 일관성 | 데이터 로딩 실패 시: 토스트 + 인라인 "다시 시도" 버튼. 네트워크 에러: "연결을 확인해주세요" + 재시도. API 타임아웃: 적절한 안내. |
| FE | 마이크로 인터랙션 강화 | 버튼 클릭: active 상태 scale(0.97) 효과. 카드 hover: lift(translateY -2px) + shadow 강화. 모달 열림/닫힘: 부드러운 opacity + scale 전환. 탭 전환: 하단 인디케이터 슬라이딩. |
| FE | 디자인 일관성 점검 | 전체 CSS에서 spacing, font-size, border-radius, shadow 일관성 점검. 누락된 CSS 변수 교체 (하드코딩 잔존분). 다크/라이트 모드 전환 시 깨지는 부분 수정. |

**체크포인트:**
- [ ] 모든 뷰의 빈 상태에 적절한 안내 + CTA
- [ ] 모든 로딩에 스켈레톤 UI
- [ ] 에러 시 토스트 + 재시도 옵션
- [ ] 다크/라이트 모드 전환 시 깨짐 0건
- [ ] 전체적인 "느낌"이 프로덕트 수준

---

### S10-7: Sprint 10 통합 QA (Day 9-10)

**통합 QA 체크리스트:**

그래프 인사이트:
- [x] 인사이트 패널 4섹션 (클러스터/트렌드/고립/허브)
- [x] 클러스터 시각화 (색상 구분 + 줌인)
- [x] "연결 만들기" 동작
- [x] 노드 더블클릭 → 상세 모달
- [x] 클러스터 → Socrates 대화 연결

대시보드:
- [x] 허브 레이아웃 (브리핑 + 퀵 액션 + 통계)
- [x] 히트맵 가독성 (라벨 + 툴팁 + 범례)
- [x] AI 인사이트 카드
- [x] 퀵 액션 4개 → 각 뷰 이동

UX 디테일:
- [x] 빈 상태 전체 일관성
- [x] 로딩 스켈레톤 전체
- [x] 에러 상태 토스트 + 재시도
- [x] 마이크로 인터랙션
- [x] 다크/라이트 전환 깨짐 0건

---

### Sprint 10 진행 체크리스트

- [x] S10-1: 그래프 인사이트 분석 엔진
- [x] S10-2: 인사이트 패널 UI + 클러스터 시각화
- [x] S10-3: 대시보드 허브 재설계
- [x] S10-4: 대시보드 AI 인사이트
- [x] S10-5: 그래프 → 다른 뷰 연결 강화
- [x] S10-6: 전체 UX 디테일 폴리싱
- [x] S10-7: 통합 QA

---

## 25. Sprint 11: 관리 체계 완성 + 프로덕션 배포 (~10일)

**테마:** "정리하는 재미 + 세상에 내놓기" — 고급 검색/중복 감지/리포트 + 실제 배포

**전략적 배경:**

Sprint 8~10에서 5개 핵심 뷰(Chat, Memory, Journal, Graph, Dashboard)의 깊이를 10/10 수준으로 끌어올렸다. Sprint 11은 두 가지 축으로 진행한다: (1) 메모리가 50개, 100개 넘어갔을 때의 **관리 체계** 완성, (2) 기능 완성 후 **프로덕션 배포**. 배포를 이 시점에 하는 이유는, 기능이 완성된 상태에서 배포해야 지인 테스트에서 의미있는 피드백을 받을 수 있기 때문이다.

```
┌─────────────────────────────────────────────────────────────────┐
│                    스프린트 11 일정 계획 (~10일)                    │
│                                                                 │
│  Track A (관리 체계)                 Track B (배포)              │
│  ──────────────────────────        ──────────────────────────   │
│  Day 1-2:                           Day 7:                      │
│  S11-1 고급 검색 필터 + 정렬         S11-4 프로덕션 환경 구성     │
│                                                                 │
│  Day 3-4:                           Day 8:                      │
│  S11-2 중복 감지 + 병합              S11-5 빌드 + 배포 + CI      │
│                                                                 │
│  Day 5-6:                                                       │
│  S11-3 주간/월간 AI 리포트                                       │
│                                                                 │
│  Day 9-10: S11-6 배포 검증 + 통합 QA                            │
└─────────────────────────────────────────────────────────────────┘
```

---

### S11-1: 고급 검색 필터 + 정렬 (Day 1-2) — 풀스택

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | `GET /memories` 쿼리 확장 | 필터: `?tags=AI,생산성` (AND), `?source_type=WEB|KAKAO|EXTENSION|MANUAL`, `?date_from=&date_to=` (범위), `?q=텍스트검색`. 정렬: `?sort_by=created_at|updated_at|title` + `?sort_order=asc|desc`. Supabase 쿼리 빌더 체이닝. |
| FE | MemoryView 필터 바 | 상단 필터 바: 태그 멀티셀렉트 (자동완성), 소스 타입 칩, 날짜 범위, 정렬 드롭다운. 필터 변경 → debounce 300ms → API 재호출. 활성 필터 수 배지. "필터 초기화" 버튼. |
| FE | 커맨드 팔레트 필터 문법 | Ctrl+K에서 `tag:AI`, `source:web`, `from:2026-01-01` 문법 지원. 실시간 파싱 → 필터 적용 → 결과 표시. |

**체크포인트:**
- [ ] 태그 "AI" 필터 → AI 태그 메모리만 표시
- [ ] 날짜 범위 필터 → 해당 기간 메모리만
- [ ] 필터 조합 동작 (태그 + 소스 + 날짜)
- [ ] 커맨드 팔레트 `tag:AI` 동작

---

### S11-2: 메모리 중복 감지 + 병합 (Day 3-4) — 풀스택

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | `GET /memories/duplicates` | URL 정확 매칭 + 벡터 유사도 0.92+ 기반 중복 감지. 수동 트리거 (비용 절감). |
| BE | `POST /memories/merge` | 병합: keep_id의 태그에 merge_id의 고유 태그 합침. merge_id 삭제. KuzuDB 관계 이전. journal_memory_links 이전. |
| FE | "중복 정리" UI | MemoryView에 "중복 정리" 버튼 (메모리 10개+ 시). 클릭 → 중복 쌍 목록 모달. 각 쌍: 두 메모리 비교 + 유사도 %. "병합"/"무시" 선택. |

**체크포인트:**
- [ ] 같은 URL 메모리 → 중복 감지
- [ ] "병합" → 태그 합침 + 나머지 삭제
- [ ] 중복 0건 시 "중복이 없습니다" 메시지

---

### S11-3: 주간/월간 AI 리포트 (Day 5-6) — 풀스택

| 구분 | 작업 | 상세 |
|------|------|------|
| BE | `GET /reports/weekly`, `/monthly` | 주간: 수집 메모리 수, 소스별 비율, 주제 Top 3, 저널 횟수, 대화 세션 수, LLM 1줄 요약. 월간: 주간 확장 + 주별 트렌드 비교. StatsService + NudgeService 재활용. |
| FE | DashboardView 리포트 탭 | 탭 추가: 브리핑/주간/월간. 카드형 레이아웃. 주제 분포 시각화 (CSS 기반 바 차트). LLM 요약을 히어로 카드로 상단. |
| BE | 스케줄러 자동 생성 | 매주 월요일 주간 리포트 자동 생성 + Push 알림. 매월 1일 월간 리포트. |

**체크포인트:**
- [ ] 주간 리포트 탭 → 7일 데이터 기반 표시
- [ ] LLM 요약 "이번 주에는..." 카드
- [ ] 월간 리포트 표시

---

### S11-4: 프로덕션 환경 구성 (Day 7) — 인프라

| 구분 | 작업 | 상세 |
|------|------|------|
| 인프라 | Fly.io secrets 설정 | `flyctl secrets set` 로 모든 환경 변수 주입. `.env.example` 완전 문서화. |
| 인프라 | 프론트엔드 배포 설정 | Vercel 배포 (정적 사이트 최적화). `.env.production` 생성. |
| 인프라 | CORS + OAuth 리다이렉트 | 프로덕션 도메인 등록. Supabase OAuth 리다이렉트 URL 추가. |

**체크포인트:**
- [ ] 모든 환경 변수 프로덕션에 등록
- [ ] `.env.production` 생성 완료
- [ ] Supabase OAuth 프로덕션 설정

---

### S11-5: 프로덕션 빌드 + 배포 + CI (Day 8) — 인프라

| 구분 | 작업 | 상세 |
|------|------|------|
| 인프라 | 백엔드 Fly.io 배포 | `flyctl deploy` + 헬스체크 + KuzuDB 볼륨 확인. |
| 인프라 | 프론트엔드 Vercel 배포 | `vercel --prod` + SPA 라우팅 확인. |
| 인프라 | GitHub Actions CI | `.github/workflows/ci.yml`: push to main → Python pytest + TypeScript 타입체크 + npm run build. |

**체크포인트:**
- [ ] `https://memoir-ai-backend.fly.dev/docs` → Swagger UI
- [ ] 프론트엔드 프로덕션 URL → 랜딩 페이지
- [ ] OAuth 로그인 → 대시보드 진입
- [ ] GitHub Actions CI 자동 실행

---

### S11-6: 배포 검증 + 통합 QA (Day 9-10)

프로덕션 스모크 테스트:
- [ ] OAuth 로그인/로그아웃
- [ ] 메모리 추가/조회/편집/삭제 + 고급 필터
- [ ] Chat SSE 스트리밍 + 출처 표시 + 피드백
- [ ] 저널 작성/자동저장/3-panel + @멘션
- [ ] 대시보드 브리핑 + AI 인사이트 + 리포트
- [ ] GraphView 인사이트 패널
- [ ] 중복 감지 + 병합
- [ ] 글로벌 검색 Ctrl+K
- [ ] 데이터 내보내기
- [ ] 넛지 알림 설정
- [ ] HTTPS + CORS + Rate Limit

---

### Sprint 11 진행 체크리스트

- [x] S11-1: 고급 검색 필터 + 정렬 (BE 쿼리 파라미터 6개 + FE 필터바/정렬/CommandPalette 문법)
- [x] S11-2: 메모리 중복 감지 + 병합 (URL 매칭 + 벡터 유사도 0.90+ 탐지, 태그 합집합 병합)
- [x] S11-3: 주간/월간 AI 리포트 (LLM 요약 + 주제/소스 분포 + 하이라이트, 1시간 캐시)
- [x] S11-4: 프로덕션 환경 구성 (vercel.json SPA + 보안 헤더, fly.toml CORS, Dockerfile 헬스체크)
- [x] S11-5: 빌드 + 배포 + CI (GitHub Actions: FE tsc+build, BE Python 구문 검증)
- [x] S11-6: 배포 검증 + 통합 QA (정적 검증 + API 엔드포인트 + 브라우저 동작 확인)

---

## 26. Sprint 12: 배포 안정화 + E2E + 데모 + 포트폴리오 (~10일)

**테마:** "완성" — 배포 후 안정화, 자동화 테스트, 데모 모드, 프로젝트 회고

**전략적 배경:**

Sprint 11에서 프로덕션 배포가 완료되었다. Sprint 12는 세 가지 축으로 마무리한다: (1) **안정화** — 프로덕션 환경 특이 이슈 수정 + 크로스 브라우저, (2) **품질 보증** — E2E 테스트로 회귀 방지 자동화, (3) **포트폴리오** — 데모 모드로 비로그인 체험 + 프로젝트 회고로 학습 정리.

```
┌─────────────────────────────────────────────────────────────────┐
│                    스프린트 12 일정 계획 (~10일)                    │
│                                                                 │
│  Day 1-2:  S12-1 배포 후 안정화 + Dogfogging 이슈 수정          │
│  Day 3-4:  S12-2 E2E 핵심 플로우 테스트 (Playwright)            │
│  Day 5-6:  S12-3 데모 모드 (/demo)                              │
│  Day 7-8:  S12-4 최종 전체 QA + 잔여 이슈 수정                  │
│  Day 9:    S12-5 프로젝트 회고 + README + 포트폴리오 정비        │
│  Day 10:   S12-6 최종 배포 + 지인 배포 + 피드백 수집             │
└─────────────────────────────────────────────────────────────────┘
```

---

### S12-1: 배포 후 안정화 + Dogfogging 이슈 수정 (Day 1-2) — 풀스택

| 구분 | 작업 | 상세 |
|------|------|------|
| 인프라 | Fly.io 콜드 스타트 대응 | 첫 API 호출 시 "서버를 깨우고 있습니다..." 로딩 + 자동 재시도 로직. UptimeRobot 무료 모니터링으로 주기적 핑 (선택). |
| FE | 크로스 브라우저 테스트 | Chrome, Safari, Firefox에서 핵심 플로우: OAuth, Chat SSE, Tiptap 에디터, GraphView WebGL. 주요 이슈 수정. |
| ALL | Dogfogging 이슈 일괄 수정 | Sprint 11 배포 후 수집된 실사용 이슈 수정. 기술 부채 잔여분 (TD-3 카카오 전송 TODO 정리, TD-4 터치 타겟). |
| ALL | SSL/혼합 콘텐츠 점검 | HTTPS 환경에서 HTTP 리소스 요청 없는지 확인. 콘솔 워닝 0건 목표. |

**체크포인트:**
- [ ] Fly.io 콜드 스타트 시 사용자에게 로딩 안내
- [ ] Chrome/Safari/Firefox 핵심 플로우 정상
- [ ] Dogfogging 이슈 리스트 0건 잔여
- [ ] 콘솔 에러/워닝 0건

---

### S12-2: E2E 핵심 플로우 테스트 (Day 3-4) — QA

| 구분 | 작업 | 상세 |
|------|------|------|
| QA | Playwright 설치 + 설정 | `playwright.config.ts`: baseURL, Chromium only. |
| QA | 테스트 1: 인증 | 랜딩 → CTA → 로그인 페이지. 로그인 상태 → 대시보드 리다이렉트. 로그아웃 → 랜딩 복귀. |
| QA | 테스트 2: 메모리 CRUD | 추가 → 목록 표시 → 상세 모달 → 편집 → 삭제. |
| QA | 테스트 3: 채팅 | 새 대화 → 메시지 전송 → AI 응답 수신. |
| QA | 테스트 4: 저널 | 저널 접속 → 텍스트 입력 → 자동 저장. |
| QA | CI 통합 | GitHub Actions에 Playwright 추가 (선택). |

**체크포인트:**
- [ ] `npx playwright test` → 4개 파일 전항 통과
- [ ] 테스트 실행 시간 2분 이내

---

### S12-3: 데모 모드 (Day 5-6) — FE

| 구분 | 작업 | 상세 |
|------|------|------|
| FE | 샘플 데이터 | `demo-data.ts`: 10개 메모리 (다양한 소스/태그), 3개 채팅 (질의+응답+참조), 2개 저널, 그래프 데이터. |
| FE | `/demo` 라우트 | 인증 불요, 읽기 전용. API 대신 로컬 데이터. `isDemoMode` Context. CUD 시도 → "데모 모드에서는 수정할 수 없습니다" 토스트 + 회원가입 CTA. |
| FE | 랜딩 "바로 체험하기" CTA | 기존 "시작하기" 옆에 "바로 체험하기" 버튼 → `/demo`. 데모 모드 상단 배너: "데모 모드 — 실제 사용하려면 회원가입하세요". |
| FE | 주요 뷰 데모 분기 | ChatView, MemoryView, JournalView, DashboardView, GraphView에 `isDemoMode` 분기. |

**체크포인트:**
- [ ] 비로그인 `/demo` → 샘플 데이터로 채워진 대시보드
- [ ] 데모 메모리/채팅/저널/그래프 탐색 가능
- [ ] CUD 시도 → 안내 토스트
- [ ] 랜딩 → 체험 → 회원가입 전환 플로우

---

### S12-4: 최종 전체 QA + 잔여 이슈 수정 (Day 7-8)

**최종 QA 체크리스트 (Sprint 8~12 전체):**

배포 인프라:
- [ ] 프로덕션 URL → 랜딩 페이지
- [ ] OAuth 로그인 → 대시보드
- [ ] HTTPS + CORS + Rate Limit
- [ ] CI: push → 빌드 + 테스트

핵심 기능 (10/10 검증):
- [ ] **Chat**: Socrates 10개 시나리오 → 8개+ 차별화 체감. 프로필 기반 맞춤. 장기 맥락. 연결 제안. 출처 표시. 피드백. 타이핑 인디케이터. 추천 질문.
- [ ] **Memory**: 카드 정보밀도. 한국어 요약. 고급 필터 (태그/소스/날짜/정렬). 편집. 일괄 관리. 중복 감지+병합.
- [ ] **Journal**: 3-panel. @멘션 참조. AI 능동 회고. 4종 템플릿. 서버 자동 저장. 양방향 메모리 연결.
- [ ] **Graph**: 노드/엣지/라벨 가독성. 인사이트 패널 (클러스터/트렌드/고립/허브). 클러스터 시각화. 다른 뷰 연결.
- [ ] **Dashboard**: 허브 레이아웃. 브리핑 히어로. 히트맵 가독성. AI 인사이트. 퀵 액션. 주간/월간 리포트.

UX 완성도 (10/10 검증):
- [ ] 빈 상태 전체 일관성
- [ ] 로딩 스켈레톤 전체
- [ ] 에러 → 토스트 + 재시도
- [ ] 마이크로 인터랙션 (hover, click, transition)
- [ ] 다크/라이트 전환 깨짐 0건
- [ ] 반응형 (1024px, 768px, 모바일)

추가 기능:
- [ ] 데이터 내보내기 3종
- [ ] 넛지 알림 3종 + 설정
- [ ] 온보딩 위자드
- [ ] 글로벌 검색 Ctrl+K
- [ ] 데모 모드 `/demo`
- [ ] E2E 테스트 통과

---

### S12-5: 프로젝트 회고 + README + 포트폴리오 (Day 9)

| 구분 | 작업 | 상세 |
|------|------|------|
| 문서 | `PROJECT_RETROSPECTIVE.md` | Sprint 1~12 여정, 기술 스택 평가, 정량 지표, 잘한 점/개선점, 향후 로드맵. |
| 문서 | `README.md` 최종 정비 | 프로젝트 소개, 주요 기능 스크린샷, 기술 스택, 아키텍처 다이어그램, 로컬/배포 가이드. |

---

### S12-6: 최종 배포 + 지인 배포 + 피드백 수집 (Day 10)

| 구분 | 작업 | 상세 |
|------|------|------|
| 인프라 | 최종 프로덕션 배포 | Sprint 12 전체 코드 배포. 스모크 테스트. |
| 운영 | 지인 배포 | 지인 2~3명에게 URL + 간단 사용 가이드 공유. 피드백 수집 (구글 설문 또는 카카오톡). |
| 운영 | 데모 URL 공유 | 포트폴리오 방문자용 데모 URL 준비. |

**체크포인트:**
- [ ] 최종 배포 완료
- [ ] 지인 2~3명 접속 + 첫 피드백 수집
- [ ] 데모 URL 동작 확인

---

### Sprint 12 진행 체크리스트

- [ ] S12-1: 배포 후 안정화 + Dogfogging 이슈
- [ ] S12-2: E2E 테스트 (Playwright 4개 파일)
- [ ] S12-3: 데모 모드 (`/demo`)
- [ ] S12-4: 최종 전체 QA
- [ ] S12-5: 프로젝트 회고 + README
- [ ] S12-6: 최종 배포 + 지인 배포

---

## 27. Sprint 8~12 전체 의존성 그래프

```
=== Sprint 8 (~10일): UX 기반 재정비 + Socrates 시작 ===

S8-1 (저널 UX) ──┐
S8-2 (메모리/채팅/대시보드 UX) ──┤
S8-3 (Socrates 프로필) ──> S8-4 (장기 맥락) ──┤
S8-5 (그래프 시각화) ──┤
S8-6 (Supabase 최적화) ──┤
                         └──> S8-7 (통합 QA)

=== Sprint 9 (~10일): Socrates 완성 + 저널 심화 ===
(Sprint 8 완료 필수)

S9-1 (실시간 연결) ──> S9-2 (품질 튜닝) ──┐
S9-3 (저널 AI 회고) ──> S9-4 (연결 플로우) ──┤
S9-5 (채팅 UX) ──┤
S9-6 (한국어 요약) ──┤
                     └──> S9-7 (통합 QA)

=== Sprint 10 (~10일): 그래프 인사이트 + 대시보드 ===
(Sprint 9 완료 필수)

S10-1 (인사이트 엔진) ──> S10-2 (패널 UI) ──> S10-5 (뷰 연결) ──┐
S10-3 (대시보드 재설계) ──> S10-4 (AI 인사이트) ──┤
S10-6 (UX 디테일) ──┤
                     └──> S10-7 (통합 QA)

=== Sprint 11 (~10일): 관리 체계 + 배포 ===
(Sprint 10 완료 필수)

S11-1 (고급 검색) ──┐
S11-2 (중복 감지) ──┤
S11-3 (리포트) ──┤
                  └──> S11-4 (환경 구성) ──> S11-5 (배포+CI) ──> S11-6 (검증+QA)

=== Sprint 12 (~10일): 안정화 + E2E + 데모 + 회고 ===
(Sprint 11 배포 완료 필수)

S12-1 (안정화) ──┐
S12-2 (E2E) ──┤
S12-3 (데모) ──┤
               └──> S12-4 (최종 QA) ──> S12-5 (회고) ──> S12-6 (최종 배포)
```

---

## 28. Sprint 12 완료 시 예상 제품 상태

### 28.1 종합 점수표

| 평가 항목 | Sprint 1 시작 | Sprint 7 완료 | Sprint 12 완료 (목표) | 10/10 달성 근거 |
|-----------|:----------:|:----------:|:----------------:|----------------|
| 기능 범위 | 7.4 | 9.5 | **10/10** | 고급 검색, 중복 감지, AI 리포트, 데모 모드까지 "빠진 기능 없음" |
| 기능 깊이 | 5.4 | 8.5 | **10/10** | Chat: 프로필+장기맥락+연결제안+피드백. Journal: 3-panel+@멘션+AI회고. Graph: 인사이트 4종. Memory: 필터+중복+병합 |
| UX 완성도 | 4.3 | 8.5 | **10/10** | 전 화면 빈상태/로딩/에러 일관성. 마이크로 인터랙션. 디자인 불일치 0건. 다크/라이트 완벽 |
| 코드 품질 | 7.5 | 8.5 | **10/10** | E2E 테스트 4파일. CI/CD. 기술 부채 0건. RLS 전수 적용. Rate Limit. ErrorBoundary |
| PMF 준비도 | 3.3 | 8.0 | **10/10** | 프로덕션 배포 + 지인 3명 실접속 + 데모 모드 + 파운더 매일 사용 + 리텐션 루프 (넛지+리포트+브리핑) |

### 28.2 Sprint 12 완료 시 제품 상태

```
"모든 영역에서 10/10, 차별화가 명확하고, 실사용 검증된 완성품"

-- 프로덕션 배포 완료 (Fly.io + Vercel, CI/CD)
-- Socrates: 사용자 프로필 + 비판적 질문 + 연결 제안 + 패턴 발견 + 장기 맥락 + 피드백
-- Journal: 3-panel + @멘션 인라인 참조 + AI 능동 회고 + 4종 템플릿 + 서버 자동 저장
-- GraphView: 클러스터/트렌드/고립/허브 인사이트 + 다른 뷰 연결 + 가독성 완성
-- Dashboard: 허브 레이아웃 + AI 인사이트 + 히트맵 가독성 + 퀵 액션 + 리포트
-- Memory: 정보밀도 카드 + 한국어 요약 + 고급 필터 + 중복 감지 + 병합
-- 관리: 고급 검색(태그/소스/날짜/정렬) + 중복 감지+병합 + 주간/월간 AI 리포트
-- 리텐션: 브리핑 + 넛지 3종 + 스트릭 + 리포트 + AI 인사이트
-- UX: 전 화면 빈상태/로딩/에러 일관성 + 마이크로 인터랙션 + 디자인 일관성 100%
-- 품질: E2E 4파일 + CI/CD + 기술 부채 0건 + 보안(RLS, Rate Limit, CORS, 입력 검증)
-- 포트폴리오: 데모 모드 + 랜딩 + README + 프로젝트 회고
-- 실사용: 프로덕션 배포 + 지인 2~3명 + 피드백 수집
```

### 28.3 "다른 도구와 다른 점" (포트폴리오 어필 포인트)

| vs. | Memoir의 차별점 |
|-----|---------------|
| **Notion** | AI가 내 기억을 기반으로 비판적 질문을 던지고 패턴을 발견함. Notion AI는 문서 편집 보조일 뿐 |
| **Obsidian** | 수집 자동(Extension+카카오), 정리 자동(Librarian AI), 연결 자동(벡터 유사도), 인사이트 자동(클러스터 분석). Obsidian은 모두 수동 |
| **ChatGPT** | 내가 저장한 기억을 세션 간 기억. 출처 명시. 연결 제안. 사용자 프로필 기반 맞춤 응답. ChatGPT는 매번 백지 |
| **Google Keep** | 지식 그래프로 관심사 구조 시각화 + AI 인사이트 생성. 메모앱은 리스트일 뿐 |

---

## 29. 전체 타임라인 요약

```
Sprint 8  (10일)  ████████████████████ UX 기반 재정비 + Socrates 시작
Sprint 9  (10일)  ████████████████████ Socrates 완성 + 저널 심화
Sprint 10 (10일)  ████████████████████ 그래프 인사이트 + 대시보드
Sprint 11 (10일)  ████████████████████ 관리 체계 + 프로덕션 배포
Sprint 12 (10일)  ████████████████████ 안정화 + E2E + 데모 + 회고

총: 50 작업일 (10주)
```

---

## 30. 리스크 및 대응 (Sprint 8~12 공통)

| 리스크 | 영향 | 확률 | 대응 |
|--------|------|------|------|
| Socrates 프롬프트 개선 효과 미미 | 차별화 미달 | 중 | 10개 시나리오 A/B 테스트. 효과 없으면 검색 top_k 증가 + 컨텍스트 포맷 개선. |
| 그래프 인사이트 클러스터 품질 | 의미 없는 클러스터 | 중 | 최소 클러스터 크기 3개. LLM 요약으로 가독성 보장. 데이터 부족 시 안내 메시지. |
| Tiptap @멘션 확장 복잡도 | 개발 지연 | 중 | Tiptap Mention 공식 확장 기반. 구현 불가 시 드래그앤드롭으로 대체. |
| Fly.io 콜드 스타트 | 첫 접속 지연 | 높 | 로딩 안내 + 자동 재시도. UptimeRobot 무료 핑. |
| 메모리 일괄 재요약 비용 | OpenAI 비용 | 중 | gpt-4o-mini 사용 + 배치 처리 + 영어 감지 메모리만 대상. |
| 지인 피드백 수집 실패 | PMF 검증 불가 | 중 | 간단한 구글 설문 3문항. 데모 모드로 체험 유도. 직접 만나서 시연. |

---

## 31. 기존 Sprint 8 작업 재배치 최종 매핑

| 기존 작업 | 재배치 | 비고 |
|----------|:------:|------|
| S8-1 환경 구성 | **S11-4** | 기능 완성 후 배포 |
| S8-2 빌드+배포 | **S11-5** | 기능 완성 후 배포 |
| S8-3 CI/CD | **S11-5** | 배포와 함께 |
| S8-4 Socrates 강화 | **S8-3, S8-4, S9-1, S9-2** | 4개 작업으로 확장 분배 |
| S8-5 고급 검색 | **S11-1** | 관리 체계 |
| S8-6 그래프 인사이트 | **S10-1, S10-2** | 2개 작업으로 확장 |
| S8-7 리포트 | **S11-3** | 관리 체계 |
| S8-8 중복 감지 | **S11-2** | 관리 체계 |
| S8-9 Dogfogging | **S12-1** | 배포 후 안정화 |
| S8-10 E2E | **S12-2** | 최종 마무리 |
| S8-11 데모 모드 | **S12-3** | 최종 마무리 |
| S8-12 회고 | **S12-5** | 최종 마무리 |

**신규 추가 작업 (기존에 없던 것):**

| 작업 | Sprint | 근거 |
|------|:------:|------|
| S8-1 저널 UX 전면 수정 | 8 | 실사용 테스트에서 발견된 6개 결함 |
| S8-2 메모리/채팅/대시보드 UX | 8 | UI/UX 전문가 리뷰 반영 |
| S8-5 그래프 시각화 기본 수정 | 8 | 노드/엣지/라벨 가독성 문제 |
| S8-6 Supabase 최적화 | 8 | 프로덕션 대비 인프라 점검 |
| S9-1 대화 중 실시간 연결 제안 | 9 | Memoir 궁극 차별화 기능 |
| S9-3 저널 AI 능동 회고 | 9 | 저널 깊이 10/10 위한 핵심 |
| S9-5 채팅 UX 완성도 | 9 | 마이크로 인터랙션 + 빈상태 |
| S9-6 메모리 한국어 일괄 전환 | 9 | 영어 요약 잔존 문제 해결 |
| S10-3 대시보드 허브 재설계 | 10 | "허브 역할 실패" 진단 대응 |
| S10-4 대시보드 AI 인사이트 | 10 | "AI 인사이트 없음" 진단 대응 |
| S10-5 그래프→다른 뷰 연결 | 10 | 고립된 시각화 → 행동 유발 |
| S10-6 전체 UX 디테일 폴리싱 | 10 | UX 10/10 위한 마무리 |
