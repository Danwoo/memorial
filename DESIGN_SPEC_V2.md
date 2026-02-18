# Memoir 10/10 UX 개선 스펙 v2

**작성일:** 2026-02-14
**대상:** 현재 구현 상태(master 브랜치) 기준
**목표:** UX 완성도 4.3/10 --> 10/10 달성을 위한 화면별 구체적 인터랙션/레이아웃/컴포넌트 스펙

---

## 0. 디자인 일관성 규칙 (Design System Normalization)

현재 코드에서 발견된 불일치를 정리하고, 모든 화면에 적용할 통일 규칙을 정의한다.

### 0.1 Border Radius 통일

**현재 문제:** `.briefing-card`는 12px, `.streak-card`는 16px, `.activity-section`은 16px, `.stat-card`는 12px로 혼재.

**규칙:**
| 요소 유형 | border-radius | CSS 변수 |
|-----------|---------------|----------|
| 소형 칩/뱃지 | 4px | `--radius-sm` |
| 인풋/버튼/카드 내부 요소 | 8px | `--radius-md` |
| 카드/패널/모달 | 12px | `--radius-lg` |
| 모달/대형 패널 | 16px | `--radius-xl` |
| 필/태그/아바타 | 9999px | `--radius-full` |

**적용:** 모든 `.card` 클래스는 `--radius-lg`(12px) 통일. 16px은 모달/대형 패널에만 사용. streak-card, activity-section, tags-section의 border-radius를 12px로 변경.

### 0.2 Typography Scale 통일

**현재 문제:** 섹션 제목이 `.dashboard-title`은 1.5rem, `.activity-section h2`는 1rem으로 페이지 내에서도 불일치.

**규칙:**
| 용도 | 크기 | 무게 | CSS 변수 |
|------|------|------|----------|
| 페이지 제목 | 1.375rem (22px) | 600 | `--fs-headline` |
| 섹션 제목 | 1rem (16px) | 600 | `--fs-title` |
| 본문 | 0.875rem (14px) | 400 | `--fs-body` |
| 보조 텍스트 | 0.8125rem (13px) | 400 | `--fs-body-sm` |
| 라벨/캡션 | 0.75rem (12px) | 500 | `--fs-label` |
| 마이크로 캡션 | 0.6875rem (11px) | 500 | `--fs-caption` |

### 0.3 Spacing 규칙

**규칙:** 4px 그리드 준수. 요소 간 간격은 8px(--space-2), 12px(--space-3), 16px(--space-4), 24px(--space-6) 4단계만 사용.

| 맥락 | 간격 |
|------|------|
| 카드 내부 요소 간 | 8px |
| 카드 내부 섹션 간 | 12px |
| 카드 패딩 | 16px |
| 섹션 간 간격 | 24px |
| 페이지 좌우 패딩 (데스크탑) | 24px |
| 페이지 좌우 패딩 (모바일) | 16px |

### 0.4 버튼 시스템 통일

**현재 문제:** `.journal-save-btn`, `.btn-primary`, `.send-button`, `.add-memory-btn` 등 각 화면에서 버튼 스타일이 독립적으로 정의됨.

**규칙:** 모든 버튼은 `index.css`에 정의된 `.btn`, `.btn-primary`, `.btn-secondary`, `.btn-ghost`, `.btn-sm` 클래스만 사용한다.

| 버튼 유형 | 용도 | 예시 |
|-----------|------|------|
| `btn btn-primary` | 주요 CTA (저장, 전송, 추가) | 저장, 추가, 검색 |
| `btn btn-secondary` | 보조 액션 (취소, 필터) | 취소, 필터, 선택 |
| `btn btn-ghost` | 텍스트만 (인라인 액션) | 더보기, 초기화 |
| `btn btn-sm` | 소형 (칩 내부, 인라인) | 태그 제거, 답변 작성 |

### 0.5 빈 상태 표현 통일

**현재 문제:** 빈 상태가 화면마다 구조와 아이콘 크기가 다름.

**규칙:** 모든 빈 상태는 다음 구조를 따른다:

```
[아이콘: Lucide 48px, color: --text-muted, opacity: 0.4]
[제목: --fs-title, weight: 400, color: --text-primary, margin-top: 8px]
[설명: --fs-body, color: --text-secondary, margin-top: 4px]
[CTA 버튼 (선택): btn btn-primary, margin-top: 16px]
```

### 0.6 색상 통일 (하드코딩 제거)

**현재 문제:** `.streak-icon`에 `#f97316` 하드코딩, similarity-badge에 `#10b981`, `#f59e0b`, `#6b7280` 하드코딩.

**규칙:** 시맨틱 색상 추가 정의:
```css
:root {
  --color-streak: #f97316;           /* 스트릭 불꽃 */
  --similarity-high: var(--color-success);
  --similarity-medium: var(--color-warning);
  --similarity-low: var(--text-muted);
}
```

---

## 1. Dashboard (대시보드)

### 1.1 현재 상태 --> 목표 상태

| 항목 | 현재 | 목표 |
|------|------|------|
| 네비게이션 위치 | 사이드바 5번째 | 사이드바 1번째 (허브 역할 복원) |
| 레이아웃 | max-width: 720px 단일 컬럼 | max-width: 960px 2컬럼 그리드 |
| 히트맵 | auto-fill 14px 셀, 구조 없음 | 7열(요일) x N행(주) GitHub 스타일 그리드 |
| 통계 카드 | 숫자 3개만 (전체/주/월) | 4개 카드 + 트렌드 화살표 + 비교 문구 |
| AI 인사이트 | 없음 | "이번 주 발견" 카드 (자동 생성) |
| 루프 시각화 | 없음 | 수집-대화-회고 3단계 진행 바 |

### 1.2 네비게이션 순서 변경

사이드바 `NAV_ITEMS` 배열 순서를 변경한다:

```typescript
const NAV_ITEMS: NavItem[] = [
  { to: '/dashboard', icon: <BarChart3 size={20} />, label: '대시보드' },
  { to: '/chat',      icon: <MessageSquare size={20} />, label: '대화' },
  { to: '/memories',  icon: <BookOpen size={20} />,      label: '기억' },
  { to: '/journal',   icon: <PenLine size={20} />,       label: '저널' },
  { to: '/graph',     icon: <Network size={20} />,       label: '그래프' },
  { to: '/settings',  icon: <SettingsIcon size={20} />,  label: '설정' },
]
```

**설계 근거:** Dashboard는 "오늘 뭘 해야 하지?"의 시작점이다. Jakob의 법칙에 따라 사용자가 가장 먼저 찾는 허브를 최상단에 배치한다. NotebookLM의 소스 패널이 항상 좌측 첫 번째인 것과 동일한 이유.

### 1.3 정보 구조 개선

```
+------------------------------------------+
| 대시보드                            [날짜] |
+------------------------------------------+
|                                          |
|  +-- 오늘의 루프 진행 바 (전체 너비) -----+ |
|  | 수집 [3/5] --> 대화 [1/2] --> 회고 [0/1]| |
|  +---------------------------------------+ |
|                                          |
|  +-- 브리핑 그리드 (2열) ----------------+ |
|  | [오늘의 메모리] | [미회고 메모리]       | |
|  | [오늘의 질문 (전체 너비)]              | |
|  | [연결 발견 (전체 너비)]                | |
|  +---------------------------------------+ |
|                                          |
|  +-- 통계 (4열) -------------------------+ |
|  | 전체 | 이번 주 | 이번 달 | 연속 기록   | |
|  +---------------------------------------+ |
|                                          |
|  +-- 2열 레이아웃 -----------------------+ |
|  | [활동 히트맵]    | [주요 주제]          | |
|  | (GitHub 스타일)  | (수평 막대 차트)     | |
|  +---------------------------------------+ |
|                                          |
+------------------------------------------+
```

### 1.4 루프 진행 바 (신규 컴포넌트)

"AI가 내 기억을 안다"를 시각화하는 핵심 UI. 수집-대화-회고 루프를 매일의 진행 상태로 표시.

```
구조:
[수집] -----> [대화] -----> [회고]
  3개          1회           미완료
 (완료)       (진행중)       (대기)

상태별 스타일:
- 완료: accent-primary 배경 + 체크 아이콘
- 진행중: accent-primary 텍스트 + 아웃라인
- 대기: text-muted + dashed border

클릭 인터랙션:
- "수집" 클릭 --> /memories
- "대화" 클릭 --> /chat
- "회고" 클릭 --> /journal

CSS 스펙:
.loop-progress {
  display: flex;
  align-items: center;
  gap: 0;
  padding: 16px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-lg);
}
.loop-step {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  padding: 12px 16px;
  cursor: pointer;
  border-radius: var(--radius-md);
  transition: background var(--transition-fast);
}
.loop-step:hover {
  background: var(--bg-tertiary);
}
.loop-connector {
  width: 40px;
  height: 2px;
  background: var(--border-secondary);
  flex-shrink: 0;
}
.loop-connector.active {
  background: var(--accent-primary);
}
```

### 1.5 히트맵 개선 (GitHub 스타일)

**현재 문제:** `grid-template-columns: repeat(auto-fill, 14px)`로 날짜별 컨텍스트가 없음. 몇 월 며칠인지, 무슨 요일인지 알 수 없다.

**개선:**
```
      월  화  수  목  금  토  일
2주전 [ ][ ][ ][ ][ ][ ][ ]
1주전 [ ][ ][ ][ ][ ][ ][ ]
이번주 [*][ ][ ][ ][ ][ ][ ]

범례: 적음 [  ] [  ] [  ] [  ] 많음
```

```css
.heatmap-grid {
  display: grid;
  grid-template-columns: auto repeat(7, 14px);
  gap: 3px;
  align-items: center;
}
.heatmap-week-label {
  font-size: var(--fs-caption);
  color: var(--text-muted);
  text-align: right;
  padding-right: 6px;
  white-space: nowrap;
}
.heatmap-day-header {
  font-size: var(--fs-caption);
  color: var(--text-muted);
  text-align: center;
}
```

**인터랙션:**
- 셀 호버: 툴팁으로 "2월 14일 (금) - 5개 기록" 표시
- 셀 클릭: 해당 날짜의 저널로 이동 (`navigate('/journal', { state: { date } })`)

### 1.6 통계 카드 개선

**현재 문제:** 데이터 적을 때 "19/19/19"처럼 모든 숫자가 동일하여 정보가치 없음.

**개선:** 4개 카드로 확장 + 트렌드 비교 표시

```
+----------+ +----------+ +----------+ +----------+
| 전체 기억 | | 이번 주  | | 이번 달  | | 연속     |
| 142      | | 12       | | 47       | | 7일      |
| +8 이번달 | | +3 지난주| | +15 전월 | | 최장: 14 |
+----------+ +----------+ +----------+ +----------+
```

```typescript
interface StatCard {
  label: string
  value: number
  trend: {
    value: number      // 이전 기간 대비 증감
    label: string      // "지난주 대비", "전월 대비"
    direction: 'up' | 'down' | 'same'
  }
}
```

```css
.stat-trend {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-caption);
  margin-top: 4px;
}
.stat-trend.up { color: var(--color-success); }
.stat-trend.down { color: var(--color-error); }
.stat-trend.same { color: var(--text-muted); }
```

### 1.7 레이아웃 CSS

```css
.dashboard-view {
  max-width: 960px;         /* 720px --> 960px */
  margin: 0 auto;
  padding: 24px;
}
.dashboard-title {
  font-size: var(--fs-headline);  /* 1.5rem --> 1.375rem 통일 */
  font-weight: 600;
}
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}
.dashboard-grid-full {
  grid-column: 1 / -1;
}

@media (max-width: 767px) {
  .dashboard-view { padding: 16px; padding-top: 52px; }
  .dashboard-grid { grid-template-columns: 1fr; }
}
```

### 1.8 반응형 브레이크포인트

| 브레이크포인트 | 레이아웃 |
|---------------|---------|
| >= 768px | 2열 그리드, 통계 4열 |
| < 768px | 1열 스택, 통계 2열, 히트맵 5주만 표시 |

---

## 2. Chat (Socrates)

### 2.1 현재 상태 --> 목표 상태

| 항목 | 현재 | 목표 |
|------|------|------|
| 헤더 | "Socrates / 당신의 지적 동반자" 고정 | 세션 컨텍스트 표시 (제목, 참조 메모리 수, 세션 시간) |
| 참조 메모리 | 페이지 이동 (`navigate('/memories')`) | 인라인 모달 (`MemoryDetailModal` 호출) |
| 입력창 | 텍스트만 | 텍스트 + @멘션 자동완성 |
| 빈 상태 | 일반적인 제안 질문 | 개인화된 "오늘의 기억 기반" 질문 카드 |
| AI 상태 | 점(...)만 | 타이핑 애니메이션 + "기억을 검색 중" 상태 표시 |
| 메시지 구분 | 아이콘만으로 구분 | 아바타 + 배경색 + 정렬로 구분 |

### 2.2 헤더 컨텍스트 바

**현재:** `<h1>Socrates</h1><p>당신의 지적 동반자</p>` -- 항상 동일한 정적 텍스트.

**개선:**

```
+------------------------------------------------------+
| Socrates                                     [새대화] |
| "최근 관심사에 대해" | 3개 기억 참조 | 15분 전 시작    |
+------------------------------------------------------+
```

세션이 없을 때(빈 상태):
```
+------------------------------------------------------+
| Socrates                                     [새대화] |
| 당신의 지적 동반자                                     |
+------------------------------------------------------+
```

```typescript
// 헤더 상태 로직
const headerSubtitle = useMemo(() => {
  if (!sessionId || messages.length === 0) {
    return '당신의 지적 동반자'
  }
  const refCount = messages.reduce((acc, m) => acc + (m.references?.length || 0), 0)
  const parts: string[] = []
  if (currentSessionTitle) parts.push(`"${currentSessionTitle}"`)
  if (refCount > 0) parts.push(`${refCount}개 기억 참조`)
  return parts.join(' | ')
}, [sessionId, messages, currentSessionTitle])
```

### 2.3 참조 메모리 인라인 모달

**현재 문제:** `onClick={() => navigate('/memories')}` -- 대화 컨텍스트를 완전히 벗어나 기억 목록 페이지로 이동.

**개선:** `MemoryDetailModal`을 직접 호출하여 대화 맥락 유지.

```typescript
// 변경 전
onClick={() => navigate(`/memories`)}

// 변경 후
onClick={() => setSelectedMemoryId(ref.id)}

// ChatView 하단에 추가
{selectedMemoryId && (
  <MemoryDetailModal
    memoryId={selectedMemoryId}
    onClose={() => setSelectedMemoryId(null)}
    onDeleted={() => setSelectedMemoryId(null)}
  />
)}
```

**설계 근거:** 참조 메모리를 확인한 후 대화를 이어가는 것이 자연스러운 사용자 플로우. 페이지 이동은 사용자의 작업 기억(working memory)을 파괴한다. Fitts의 법칙: 모달은 현재 시선 근처에서 열리므로 탐색 비용이 낮다.

### 2.4 @멘션 자동완성

입력창에서 `@`를 입력하면 최근 메모리 목록이 드롭업으로 표시된다.

```
+--------------------------------------------------+
| @마케                                             |
+--------------------------------------------------+
| 최근 메모리                                        |
| [WEB] 마케팅 전략 2026                    2시간 전  |
| [NOTE] 마케팅 비용 분석                   어제      |
| [PDF] 콘텐츠 마케팅 가이드                3일 전    |
+--------------------------------------------------+
```

**인터랙션 상세:**
1. 사용자가 `@` 입력 --> 멘션 드롭업 표시
2. 추가 텍스트 입력 --> 실시간 필터링 (벡터 검색 API 호출, 300ms 디바운스)
3. 화살표 키 --> 항목 선택
4. Enter 또는 클릭 --> 멘션 삽입: `@[메모리 제목](memory-id)` 형태로 입력 텍스트에 삽입
5. Escape --> 드롭업 닫기

```css
.mention-dropdown {
  position: absolute;
  bottom: 100%;
  left: 0;
  right: 0;
  max-height: 240px;
  overflow-y: auto;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  margin-bottom: 8px;
  z-index: 50;
}
.mention-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background var(--transition-fast);
}
.mention-item:hover,
.mention-item.active {
  background: var(--accent-bg);
}
.mention-item-icon {
  flex-shrink: 0;
  color: var(--text-muted);
}
.mention-item-title {
  flex: 1;
  font-size: var(--fs-body-sm);
  color: var(--text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.mention-item-date {
  font-size: var(--fs-caption);
  color: var(--text-muted);
  flex-shrink: 0;
}
```

### 2.5 AI 응답 상태 표시 개선

**현재:** `<span className="typing-indicator">...</span>` -- 단순 점 3개 깜빡임.

**개선:** 2단계 상태 표시

```
1단계: "기억을 검색하고 있습니다..." (벡터 검색 진행 중)
2단계: 텍스트 스트리밍 (현재와 동일)
```

```css
.thinking-indicator {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  color: var(--text-secondary);
  font-size: var(--fs-body-sm);
}
.thinking-dots {
  display: flex;
  gap: 4px;
}
.thinking-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--accent-primary);
  animation: thinking-bounce 1.4s ease-in-out infinite;
}
.thinking-dot:nth-child(2) { animation-delay: 0.2s; }
.thinking-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes thinking-bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}
```

### 2.6 빈 상태 개선 - "AI가 내 기억을 안다"

**현재:** 일반적인 제안 질문 버튼.

**개선:** 브리핑 데이터를 활용한 개인화 빈 상태.

```
+--------------------------------------------------+
|                                                  |
|            [Socrates 아바타 아이콘]                |
|                                                  |
|     오늘 3개의 새로운 기억이 쌓였습니다              |
|     #마케팅 #개발 #디자인                          |
|                                                  |
|  +--------------------------------------------+  |
|  | "오늘 저장한 마케팅 전략 글에서              |  |
|  |  가장 인상적인 부분은 뭐였어?"               |  |
|  +--------------------------------------------+  |
|  +--------------------------------------------+  |
|  | "최근 관심사에 대해 이야기해줘"              |  |
|  +--------------------------------------------+  |
|  +--------------------------------------------+  |
|  | "저장한 글 중 인상적인 것은?"                |  |
|  +--------------------------------------------+  |
|                                                  |
+--------------------------------------------------+
```

**핵심 차별화:** 첫 번째 제안 질문은 AI가 오늘 수집된 메모리를 기반으로 자동 생성한 것. 사용자가 "이 AI는 내가 오늘 뭘 했는지 알고 있구나"를 느끼게 한다.

### 2.7 반응형

| 브레이크포인트 | 변경 |
|---------------|------|
| >= 768px | message-content max-width: 70% |
| < 768px | message-content max-width: 85%, 헤더 padding-left: 52px (햄버거 공간) |

---

## 3. Memories (기억)

### 3.1 현재 상태 --> 목표 상태

| 항목 | 현재 | 목표 |
|------|------|------|
| 카드 정보 | 제목 + 영문 요약 + 날짜 | 제목 + 한국어 요약 + 소스 아이콘 + 태그(최대 3) + 연결 수 + 상대 시간 |
| 전체 탭 | 정렬/필터 없음 | 정렬 드롭다운 (최신순/오래된순/제목순) + 소스 필터 칩 |
| 카드 호버 | translateY(-2px) + shadow | translateY(-2px) + shadow + 좌측 accent 보더 |
| 빈 상태 | 일반 텍스트 | 일러스트 + 3가지 수집 방법 안내 |

### 3.2 메모리 카드 개선

```
+----------------------------------------------+
| [WEB 아이콘]                          2시간 전 |
|                                              |
| 마케팅 자동화 전략 가이드 2026                 |
|                                              |
| AI가 자동 생성한 한국어 요약 텍스트가 여기에    |
| 최대 2줄까지 표시됩니다...                     |
|                                              |
| #마케팅 #자동화 #전략        3개 연결          |
+----------------------------------------------+
```

```typescript
// 카드 컴포넌트 Props
interface MemoryCardProps {
  memory: Memory
  onSelect: (id: string) => void
  isSelected?: boolean      // 선택 모드
  selectMode?: boolean
}
```

```css
.memory-card {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: all var(--transition-fast);
  border-left: 3px solid transparent;
}
.memory-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--shadow-md);
  border-left-color: var(--accent-primary);
}

.memory-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.memory-card-source {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--fs-caption);
  color: var(--text-muted);
}
.memory-card-time {
  font-size: var(--fs-caption);
  color: var(--text-muted);
}

.memory-card-title {
  font-size: var(--fs-title);
  font-weight: 500;
  color: var(--text-primary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.memory-card-summary {
  font-size: var(--fs-body-sm);
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  line-height: 1.5;
}

.memory-card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: auto;
}
.memory-card-tags {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}
.memory-card-tag {
  font-size: var(--fs-caption);
  color: var(--accent-primary);
  background: var(--accent-bg);
  padding: 1px 6px;
  border-radius: var(--radius-full);
}
.memory-card-connections {
  font-size: var(--fs-caption);
  color: var(--text-muted);
  display: flex;
  align-items: center;
  gap: 4px;
}
```

### 3.3 전체 탭 정렬/필터

헤더와 탭 사이에 필터 바 추가:

```
+--------------------------------------------------+
| 기억                                     [선택][추가] |
+--------------------------------------------------+
| 전체 | 타임라인 | 검색                             |
+--------------------------------------------------+
| 정렬: [최신순 v]  | 소스: [전체] [WEB] [PDF] [NOTE] |
+--------------------------------------------------+
| [카드 그리드]                                      |
+--------------------------------------------------+
```

```css
.memory-filter-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 24px;
  border-bottom: 1px solid var(--border-secondary);
  gap: 12px;
}
.memory-sort-select {
  padding: 4px 8px;
  font-size: var(--fs-body-sm);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-md);
  background: var(--bg-card);
  color: var(--text-primary);
  cursor: pointer;
}
.memory-source-filters {
  display: flex;
  gap: 4px;
}
.source-filter-chip {
  padding: 4px 10px;
  font-size: var(--fs-caption);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-full);
  background: transparent;
  color: var(--text-secondary);
  cursor: pointer;
  transition: all var(--transition-fast);
}
.source-filter-chip.active {
  background: var(--accent-primary);
  color: var(--text-inverse);
  border-color: var(--accent-primary);
}
.source-filter-chip:hover:not(.active) {
  border-color: var(--accent-primary);
  color: var(--accent-primary);
}
```

### 3.4 영어 요약 --> 한국어 요약

**현재 문제:** 백엔드 Librarian 에이전트가 영어로 요약을 생성하여 한국어 서비스에서 인지 부조화 발생.

**해결:** 백엔드 Librarian 에이전트의 프롬프트에 `"반드시 한국어로 요약하세요"` 지시를 추가. 이것은 프론트엔드 스펙이 아니라 백엔드 수정 사항이지만, UX 임팩트가 크므로 명시.

---

## 4. Journal (저널)

### 4.1 현재 상태 --> 목표 상태

| 항목 | 현재 | 목표 |
|------|------|------|
| 레이아웃 | 에디터(좌) + 사이드바(우, collapsed 기본) | 에디터(중앙) + AI패널(우측) 상시 표시, 사이드바 토글 |
| 관련 메모리 클릭 | 무반응 (insert만 가능) | 클릭: MemoryDetailModal, 드래그: 에디터에 삽입 |
| 자동 저장 | localStorage 2초 디바운스 | localStorage + 서버 저장 인디케이터 (저장 중.../저장됨) |
| 캘린더 | 드롭다운 리스트 | 미니 캘린더 위젯 (월별 뷰) |
| AI 패널 | 에디터 아래 접힘 패널 | 우측 상시 패널 (데스크탑) / 하단 패널 (태블릿) |

### 4.2 3-Panel 레이아웃 (데스크탑)

```
+----------------------------------------------------------+
| [<] 2월 14일 금요일 [>] [오늘]              [저장됨 ✓]      |
+----------------------------------------------------------+
| [편집] [마크다운] [미리보기]                                |
+----------------------------------------------------------+
|                              |                            |
|                              | [오늘의 메모리] [관련]       |
|   에디터 영역                 |                            |
|   (flex: 1)                  | [메모리 카드 1]             |
|                              | [메모리 카드 2]             |
|                              | [메모리 카드 3]             |
|                              |                            |
|                              | ---- AI 액션 ----          |
|                              | [하루 정리] [세션 초안]      |
|                              |                            |
+------------------------------+----------------------------+
|           AI 분석 패널 (접기/펼치기)                        |
+----------------------------------------------------------+
```

### 4.3 자동 저장 상태 인디케이터

헤더 우측에 저장 상태를 항상 표시:

```
상태 전이:
편집 중 (변경 감지) --> "저장 중..." (디바운스 후) --> "저장됨" (2초 후 페이드)
                                                     |
                                                     V (에러 시)
                                                  "저장 실패" (빨간색)
```

```css
.autosave-indicator {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: var(--fs-caption);
  color: var(--text-muted);
  transition: all var(--transition-normal);
}
.autosave-indicator.saving {
  color: var(--text-secondary);
}
.autosave-indicator.saved {
  color: var(--color-success);
}
.autosave-indicator.error {
  color: var(--color-error);
}
```

### 4.4 미니 캘린더 위젯

현재 드롭다운 리스트를 월별 캘린더로 교체.

```
+-------------------------------+
|  < 2026년 2월 >               |
|  월 화 수 목 금 토 일          |
|                          1    |
|   2  3  4  5  6  7  8        |
|   9 10 11 12 13 [14] 15      |
|  16 17 18 19 20  21  22      |
|  23 24 25 26 27  28          |
+-------------------------------+
| * 저널이 있는 날짜는 점으로 표시 |
+-------------------------------+
```

**인터랙션:**
- 저널이 있는 날짜: 하단에 작은 점(accent-primary) 표시
- 날짜 클릭: 해당 날짜 저널로 이동
- 오늘 날짜: accent-primary 배경 원형 강조
- 선택된 날짜: accent-bg 배경
- 월 이동: `<` `>` 버튼으로 이전/다음 월

```css
.mini-calendar {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 4px;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-lg);
  padding: 12px;
  z-index: 50;
  width: 280px;
}
.calendar-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 2px;
  text-align: center;
}
.calendar-day {
  width: 32px;
  height: 32px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: var(--fs-body-sm);
  cursor: pointer;
  position: relative;
  border: none;
  background: none;
  color: var(--text-primary);
  transition: background var(--transition-fast);
}
.calendar-day:hover {
  background: var(--bg-tertiary);
}
.calendar-day.today {
  background: var(--accent-primary);
  color: var(--text-inverse);
  font-weight: 600;
}
.calendar-day.selected {
  background: var(--accent-bg);
  color: var(--accent-primary);
  font-weight: 600;
}
.calendar-day.has-journal::after {
  content: '';
  position: absolute;
  bottom: 2px;
  width: 4px;
  height: 4px;
  border-radius: 50%;
  background: var(--accent-primary);
}
.calendar-day.today.has-journal::after {
  background: var(--text-inverse);
}
```

### 4.5 관련 메모리 클릭 동작

**현재 문제:** MemoryCard 컴포넌트의 클릭은 `onInsertMemory`만 호출. 메모리 상세를 볼 방법이 없음.

**개선:** 두 가지 인터랙션 분리
- **클릭:** MemoryDetailModal 열기
- **드래그 or "삽입" 버튼:** 에디터에 삽입

```typescript
// MemoryCard에 onDetail prop 추가
interface MemoryCardProps {
  memory: DigestMemory | RelatedMemory
  onInsert: (memory: DigestMemory | RelatedMemory) => void
  onDetail?: (memory: DigestMemory | RelatedMemory) => void  // 신규
}
```

### 4.6 반응형

| 브레이크포인트 | 레이아웃 |
|---------------|---------|
| >= 1280px | 에디터(flex: 1) + 사이드바(280px) 가로 배치 |
| 1024px ~ 1279px | 에디터(flex: 1) + 사이드바(240px) 가로 배치 |
| < 1024px | 에디터(100%) + 사이드바(하단 접힘 패널) |
| < 768px | 에디터 전체화면 + 사이드바 hidden (FAB 토글) |

---

## 5. Graph (지식 그래프)

### 5.1 현재 상태 --> 목표 상태

| 항목 | 현재 | 목표 |
|------|------|------|
| 노드 크기 | `Math.max(1.5, sqrt(val) * 1.5)` (매우 작음) | `Math.max(3, sqrt(val) * 2.5)` |
| 엣지 가시성 | opacity 0.12 (거의 안보임) | opacity 0.25 (기본) / 0.8 (하이라이트) |
| 라벨 | `textHeight: max(1.2, size * 0.5)` (작음) | `textHeight: max(2, size * 0.7)` |
| 조작 안내 | 하단 고정 텍스트 4개 | 첫 3초만 표시 후 페이드아웃 (재표시: ? 아이콘) |
| 인사이트 패널 | 없음 | 좌측 하단에 "이 그래프에서 발견" 카드 |

### 5.2 노드 렌더링 개선

```typescript
const nodeThreeObject = useCallback((node: AnyNode) => {
  const val = node.val || 1
  const size = Math.max(3, Math.sqrt(val) * 2.5)  // 크기 증가
  // ...
  sprite.textHeight = Math.max(2, size * 0.7)      // 라벨 크기 증가
  // ...
}, [bgColor])
```

### 5.3 엣지 가시성 개선

```typescript
// 변경 전
linkColor={(link) =>
  highlightLinks.has(getLinkKey(link))
    ? 'rgba(255,255,255,0.8)'
    : 'rgba(255,255,255,0.12)'    // 너무 안보임
}

// 변경 후
linkColor={(link) =>
  highlightLinks.has(getLinkKey(link))
    ? (bgColor === '#1a1a1a' ? 'rgba(255,255,255,0.8)' : 'rgba(0,0,0,0.6)')
    : (bgColor === '#1a1a1a' ? 'rgba(255,255,255,0.25)' : 'rgba(0,0,0,0.15)')
}
linkWidth={(link) => (highlightLinks.has(getLinkKey(link)) ? 2 : 0.5)}
```

### 5.4 조작 안내 개선

**현재 문제:** 하단에 항상 표시되어 시각적 노이즈.

**개선:** 첫 진입 시 3초 표시 후 페이드아웃. 우측 하단 `?` 아이콘으로 재표시 가능.

```typescript
const [showControls, setShowControls] = useState(true)

useEffect(() => {
  const timer = setTimeout(() => setShowControls(false), 5000)
  return () => clearTimeout(timer)
}, [])
```

```css
.graph-controls {
  /* 기존 스타일 유지 */
  transition: opacity 0.5s ease;
}
.graph-controls.hidden {
  opacity: 0;
  pointer-events: none;
}
.graph-help-btn {
  position: absolute;
  bottom: 16px;
  right: 20px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--bg-card);
  border: 1px solid var(--border-secondary);
  color: var(--text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 10;
  transition: all var(--transition-fast);
}
.graph-help-btn:hover {
  color: var(--text-primary);
  border-color: var(--accent-primary);
}
```

### 5.5 "와우 모먼트" 시각적 설계

**목표:** 사용자가 그래프를 처음 보고 "우와" 하게 만드는 시각적 연출.

**1) 진입 애니메이션**
- 그래프 로딩 완료 후 카메라가 전체 뷰에서 천천히 줌인 (2초)
- 노드가 중앙에서 방사형으로 퍼지는 force 시뮬레이션 (기본 내장)
- 노드 페이드인: opacity 0 --> 1, 0.5초 stagger

**2) 클러스터 하이라이트**
- 연결이 많은 허브 노드에 glow 효과 추가
- 허브 노드: val 상위 5개에 pulsating 애니메이션

```typescript
// 허브 노드 glow
if (isHub) {
  mat.emissive = new THREE.Color(color)
  mat.emissiveIntensity = 0.3
}
```

**3) 인사이트 카드 (좌측 하단)**

```
+-------------------------------+
| 이 그래프에서 발견              |
|                               |
| "마케팅"과 "AI"가 가장 많이    |
| 연결되어 있습니다.              |
| 최근 관심사인 것 같습니다.      |
|                               |
| [이 주제로 대화하기]            |
+-------------------------------+
```

### 5.6 반응형

| 브레이크포인트 | 변경 |
|---------------|------|
| >= 768px | 범례 좌측 하단, 인포 패널 우측, 인사이트 좌측 |
| < 768px | 범례 숨김, 인포 패널 하단 시트, 인사이트 숨김, 조작 안내 간소화 |

---

## 6. 전체 인터랙션/마이크로 인터랙션 규격

### 6.1 전환 애니메이션

| 요소 | 트리거 | duration | easing | property |
|------|--------|----------|--------|----------|
| 카드 호버 | mouseenter | 100ms | ease-out | transform, box-shadow, border-color |
| 모달 열기 | state 변경 | 200ms | ease-out | opacity, transform(scale 0.95-->1) |
| 모달 닫기 | state 변경 | 150ms | ease-in | opacity, transform(scale 1-->0.95) |
| 페이지 전환 | route 변경 | 200ms | ease-out | opacity |
| 토스트 진입 | 호출 | 200ms | ease-out | opacity, translateY(8px-->0) |
| 토스트 퇴장 | 자동/수동 | 200ms | ease-in | opacity, translateY(0-->8px) |
| 사이드바 전환 | resize | 250ms | ease | width, transform |
| 드롭다운 열기 | 클릭 | 150ms | ease-out | opacity, translateY(-4px-->0) |

### 6.2 로딩 상태

모든 비동기 작업에는 3단계 로딩 피드백:

1. **즉시 (0-100ms):** 아무것도 안 함 (체감 안되는 지연)
2. **짧은 지연 (100-500ms):** 버튼 비활성화 + 스피너 표시
3. **긴 지연 (500ms+):** 스켈레톤 UI 또는 진행 상태 텍스트

### 6.3 스켈레톤 로딩 규격

| 화면 | 스켈레톤 구조 |
|------|-------------|
| Dashboard | 제목 바 + 카드 3개 + 히트맵 영역 |
| Chat (히스토리) | 메시지 버블 3개 (좌/우/좌) |
| Memories | 카드 그리드 6개 |
| Journal | 에디터 헤더 + 본문 라인 5개 |
| Graph | 중앙 스피너 + "지식 그래프 로딩 중..." |

### 6.4 에러 상태

모든 에러는 다음 3가지 중 하나로 표시:

1. **인라인 에러:** 해당 영역 내부에 에러 메시지 + 재시도 버튼
2. **토스트 에러:** 하단 중앙 토스트 (3초 자동 소멸, 수동 닫기 가능)
3. **전체 화면 에러:** ErrorBoundary 폴백 (이미 구현됨)

---

## 7. "AI가 내 기억을 안다" 패턴 설계

모든 화면에서 "이 AI는 나의 기억을 알고 있다"를 느끼게 하는 구체적 UI 패턴.

### 7.1 Dashboard: 맥락 인사

```
현재: "대시보드" (정적 제목)
목표: "안녕하세요, 대니. 이번 주에 마케팅과 개발에 관심이 많으셨네요."
```

대시보드 상단에 1줄 인사 메시지. 매일 브리핑 API 응답의 `connection_hint` 또는 `suggested_question`을 활용.

### 7.2 Chat: 기억 기반 대화 시작

이미 구현된 브리핑 기반 제안 질문을 강화. 첫 번째 제안은 항상 "오늘 수집한 특정 메모리"를 언급.

### 7.3 Journal: 글감 자동 제시

이미 구현된 `digest.memories`와 `starterQuestions`를 활용. 추가 개선:

```
현재: "오늘의 회고 질문" 3개 표시
목표: 질문 앞에 관련 메모리를 인용하여 맥락 제공

"오늘 저장한 [마케팅 전략 글]에서 '고객 세분화'를 강조했는데,
 이 관점이 당신의 기존 전략과 어떻게 다른가요?"
```

### 7.4 Memories: 연결 발견 하이라이트

카드 목록 상단에 "AI가 발견한 연결" 배너:

```
+--------------------------------------------------+
| [Sparkles 아이콘] AI가 새로운 연결을 발견했습니다     |
| "2주 전 저장한 [UX 리서치 방법론]과                  |
|  오늘 저장한 [사용자 인터뷰 가이드]가 연결됩니다"     |
| [연결 보기]                                        |
+--------------------------------------------------+
```

### 7.5 Graph: 클러스터 인사이트

노드 선택 시 인포 패널에 AI 한줄 코멘트:

```
현재: 노드 이름 + 연결 목록
목표: 노드 이름 + AI 코멘트 + 연결 목록

"마케팅은 당신이 가장 많이 탐구하는 주제입니다.
 12개의 메모리와 연결되어 있고, 최근 2주간 활발합니다."
```

---

## 8. 수집 --> 대화 --> 회고 루프 시각적 연결

### 8.1 설계 원칙

사용자가 Memoir의 3단계 루프를 자연스럽게 체감하도록 화면 간 연결 고리를 시각적으로 표현한다.

### 8.2 구현 방법

**1) Dashboard 루프 진행 바 (섹션 1.4 참조)**

매일의 루프 진행 상태를 시각화.

**2) Chat --> Journal 연결**

채팅 세션 하단에 "이 대화를 저널로 정리하기" CTA:

```
+--------------------------------------------------+
| [대화 메시지들...]                                  |
|                                                    |
| -------------------------------------------------- |
| [PenLine 아이콘] 이 대화를 저널로 정리하시겠어요?     |
| [저널 쓰러 가기]                                    |
+--------------------------------------------------+
```

```css
.chat-journal-cta {
  margin-top: 16px;
  padding: 12px 16px;
  background: var(--accent-bg);
  border: 1px dashed var(--accent-primary);
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--accent-primary);
  font-size: var(--fs-body-sm);
}
```

**3) Journal --> Memories 연결**

저널에 인용된 메모리는 에디터 내에서 클릭 가능한 블록으로 표시 (이미 `MemoryBlockNode` 구현됨). 추가로 메모리 상세 모달 연결.

**4) Memories --> Chat 연결**

메모리 상세 모달 하단에 "이 기억에 대해 대화하기" 버튼 추가:

```typescript
// MemoryDetailModal에 추가
<button
  className="btn btn-secondary"
  onClick={() => {
    onClose()
    navigate('/chat', { state: { topic: detail.title } })
  }}
>
  <MessageSquare size={14} />
  이 기억에 대해 대화하기
</button>
```

---

## 9. 접근성 체크리스트 (WCAG 2.1 AA)

### 9.1 키보드 네비게이션

| 요소 | Tab 순서 | Enter/Space | Escape |
|------|---------|-------------|--------|
| 사이드바 네비게이션 | 순서대로 | 해당 페이지 이동 | N/A |
| 모달 | focus trap 내부 | 버튼 클릭 | 모달 닫기 |
| 드롭다운 | 항목 순서 | 항목 선택 | 드롭다운 닫기 |
| 카드 그리드 | 좌->우, 위->아래 | 상세 모달 열기 | N/A |
| 채팅 입력 | 마지막 | 메시지 전송 | N/A |

### 9.2 ARIA 속성

| 컴포넌트 | 필수 ARIA |
|----------|----------|
| 모든 모달 | `role="dialog"`, `aria-modal="true"`, `aria-labelledby` |
| 채팅 메시지 영역 | `aria-live="polite"`, `aria-label="대화 메시지"` |
| 탭 네비게이션 | `role="tablist"`, `role="tab"`, `aria-selected` |
| 토스트 | `role="status"`, `aria-live="polite"` |
| 스켈레톤 | `aria-busy="true"`, `aria-label="로딩 중"` |
| 아이콘 전용 버튼 | `aria-label="동작 설명"` |

### 9.3 색상 대비

현재 디자인 토큰의 색상 대비율:
- `--text-primary` on `--bg-primary`: 14.5:1 (AA 합격)
- `--text-secondary` on `--bg-primary`: 6.2:1 (AA 합격)
- `--text-muted` on `--bg-primary`: 4.1:1 (AA 보더라인 -- 주의 필요)
- `--accent-primary` on `--bg-primary`: 4.6:1 (AA 합격, large text)

**주의:** `--text-muted`(#80838a)는 AA 기준 4.5:1에 미달할 수 있음. 본문 크기(14px 이하)에서 사용할 때 `--text-secondary`로 교체 검토.

---

## 10. 우선순위

### P0 (MVP 필수 - 즉시)

| # | 항목 | 예상 공수 | 근거 |
|---|------|----------|------|
| 1 | Chat 참조 메모리 클릭 시 MemoryDetailModal 호출 | 0.5d | 현재 navigate('/memories')로 맥락 끊김. 1줄 수정. |
| 2 | MemoryDetailModal에 "이 기억에 대해 대화하기" 버튼 | 0.5d | 루프 연결의 핵심. |
| 3 | 메모리 카드에 태그/연결 수/소스아이콘/상대시간 표시 | 1d | 카드 정보밀도가 너무 낮아 어떤 메모리인지 파악 불가. |
| 4 | 디자인 일관성: border-radius/typography/spacing 통일 | 1d | 섹션 0의 규칙 일괄 적용. |
| 5 | AI 응답 상태 표시 개선 (thinking indicator) | 0.5d | 현재 "..." 점만으로 AI가 뭘 하는지 모름. |

### P1 (권장 - 1-2주 내)

| # | 항목 | 예상 공수 | 근거 |
|---|------|----------|------|
| 1 | Dashboard 네비게이션 1번째 이동 + 레이아웃 개선 (960px, 2열) | 1d | 허브 역할 복원. |
| 2 | Dashboard 루프 진행 바 | 1.5d | "수집-대화-회고" 루프 시각화. 핵심 가치 전달. |
| 3 | Dashboard 히트맵 GitHub 스타일 (7열 그리드 + 툴팁) | 1d | 현재 구조 없는 점 나열은 정보가치 없음. |
| 4 | Dashboard 통계 카드 4열 + 트렌드 표시 | 0.5d | "19/19/19" 문제 해결. |
| 5 | Journal 미니 캘린더 | 1.5d | 현재 드롭다운 리스트는 날짜 탐색이 불편. |
| 6 | Memories 전체 탭 정렬/소스필터 | 1d | 메모리 많아지면 탐색 불가. |
| 7 | Graph 노드/엣지 크기 개선 | 0.5d | 현재 너무 작아 시각적 임팩트 없음. |
| 8 | Graph 조작 안내 자동 숨김 + ? 버튼 | 0.5d | 시각적 노이즈 제거. |
| 9 | Chat @멘션 자동완성 | 2d | 대화 중 특정 메모리 참조를 쉽게. |
| 10 | 영어 요약 --> 한국어 요약 (백엔드) | 0.5d | 인지 부조화 해소. |

### P2 (향후 - 1개월 내)

| # | 항목 | 예상 공수 | 근거 |
|---|------|----------|------|
| 1 | Dashboard AI 인사 메시지 | 1d | "AI가 내 기억을 안다" 체감. |
| 2 | Memories "AI 연결 발견" 배너 | 1.5d | 수동 탐색 --> 능동 제안 전환. |
| 3 | Graph 진입 애니메이션 + 허브 glow | 1d | "와우 모먼트" 연출. |
| 4 | Graph 인사이트 카드 | 2d | 시각화 + 의미 부여. |
| 5 | Chat --> Journal 연결 CTA | 0.5d | 루프 마지막 단계 유도. |
| 6 | Journal AI 질문에 메모리 인용 추가 | 1.5d | "AI가 내 기억을 안다" 저널에서 체감. |
| 7 | 전체 접근성 감사 (키보드 네비게이션, 색상 대비) | 2d | WCAG 2.1 AA 준수. |
| 8 | 모바일 완전 반응형 | 3d | 터치 인터랙션 최적화 포함. |

---

## 부록 A. 컴포넌트 트리 제안

```
App
  AuthProvider
    ThemeProvider
      ToastProvider
        AppLayout
          Sidebar
            Logo
            NewChatButton
            NavItems[]
            SessionList (Chat 페이지일 때만)
            UserSection
          MainContent
            DashboardView
              LoopProgressBar      (신규)
              BriefingGrid
              StatsGrid            (4열 개선)
              ActivityHeatmap      (GitHub 스타일)
              TopTagsChart
            ChatView
              ChatHeader           (컨텍스트 바 추가)
              ChatMessages
                MessageBubble
                  MarkdownRenderer
                  ReferenceChips   (MemoryDetailModal 연결)
                ThinkingIndicator  (신규)
              ChatInput
                MentionDropdown    (신규)
                SendButton
            MemoryView
              MemoryHeader
              MemoryTabs
              MemoryFilterBar      (신규)
              MemoryGrid
                MemoryCard         (개선)
              MemoryDetailModal
            JournalView
              JournalHeader
                DateNavigation
                MiniCalendar       (신규)
                AutosaveIndicator  (신규)
              EditorToolbar
              EditorArea
                TiptapEditor
                MarkdownEditor
                ReadOnlyViewer
              AIPanel
              MemorySidebar
            GraphView
              SearchBar
              StatsOverlay
              ForceGraph3D
              LegendPanel
              NodeInfoPanel
              InsightCard          (신규)
              HelpButton           (신규)
            SettingsView
```

---

## 부록 B. CSS 변수 추가 목록

```css
:root {
  /* 신규 시맨틱 색상 */
  --color-streak: #f97316;
  --similarity-high: var(--color-success);
  --similarity-medium: var(--color-warning);
  --similarity-low: var(--text-muted);

  /* 루프 진행 바 */
  --loop-step-size: 48px;
  --loop-connector-width: 40px;

  /* 캘린더 */
  --calendar-cell-size: 32px;

  /* 히트맵 */
  --heatmap-cell-size: 14px;
  --heatmap-gap: 3px;
}
```
