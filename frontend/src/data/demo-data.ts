import type { Memory, MemoryDetail } from '../types/memory'
import type { ChatMessage, ChatReference, ChatSessionResponse } from '../types/chat'
import type { BriefingData, StatsData, StreakData, ActivityData, DailyInsight, DigestData } from '../types/dashboard'
import type { GraphData, GraphInsights } from '../types/graph'
import type { InsightsResponse, ReviewQuestionsResponse, JournalEntry } from '../types/journal'
import type { PaginatedResponse, RelatedMemoriesResponse } from '../types/api'
import type { TimelineGroup } from '../types/timeline'
import type { ReportData } from '../api/reports'

// ─── 헬퍼 ──────────────────────────────────────────────────────────────────

export function demoPaginated<T>(items: T[], page = 1, limit = 20): PaginatedResponse<T> {
  const start = (page - 1) * limit
  return {
    items: items.slice(start, start + limit),
    total: items.length,
    page,
    limit,
    has_more: start + limit < items.length,
  }
}

// ─── 태그 ──────────────────────────────────────────────────────────────────

export const DEMO_TAGS: string[] = [
  'AI', '딥러닝', 'Transformer', 'LangGraph', '에이전트',
  '철학', '스토아', '심리학', 'CBT', '메타인지',
  'PKM', '생산성', 'Zettelkasten', '시간관리',
  '건강', '뇌과학', '운동',
  '프로그래밍', '함수형', 'FP', 'React', '프론트엔드', 'RSC',
  '데이터베이스', 'PostgreSQL', '최적화',
  '학습',
]

// ─── 메모리 ──────────────────────────────────────────────────────────────────

export const DEMO_MEMORIES: Memory[] = [
  { id: 'dm-1', title: '트랜스포머 아키텍처의 핵심: Self-Attention 메커니즘', summary: 'Self-Attention이 시퀀스 내 모든 위치 간 관계를 동시에 계산하는 방식과, 이를 통해 RNN의 순차적 한계를 극복하는 원리를 정리.', source_type: 'WEB', created_at: '2026-02-15T10:30:00Z', tags: ['AI', '딥러닝', 'Transformer'] },
  { id: 'dm-2', title: '스토아 철학과 현대 인지행동치료의 연결', summary: '에픽테토스의 "우리를 괴롭히는 것은 사건 자체가 아니라 그에 대한 판단이다"가 CBT의 인지 재구성과 직접 연결되는 점이 인상적.', source_type: 'WEB', created_at: '2026-02-14T08:15:00Z', tags: ['철학', '심리학', '스토아'] },
  { id: 'dm-3', title: '개인 지식 관리(PKM) 시스템 설계 원칙', summary: 'Zettelkasten 방식의 원자적 노트 + 양방향 링크가 창의적 사고를 촉진하는 이유. 두 번째 뇌 구축의 핵심 원칙들.', source_type: 'PDF', created_at: '2026-02-13T14:00:00Z', tags: ['PKM', '생산성', 'Zettelkasten'] },
  { id: 'dm-4', title: '운동이 뇌에 미치는 영향: 신경과학적 근거', summary: 'BDNF 증가, 해마 뉴런 생성, 전전두엽 기능 향상 등 규칙적 운동의 인지적 이점에 대한 최신 연구 정리.', source_type: 'WEB', created_at: '2026-02-12T16:45:00Z', tags: ['건강', '뇌과학', '운동'] },
  { id: 'dm-5', title: '함수형 프로그래밍의 핵심 개념 메모', summary: '불변성, 순수 함수, 고차 함수, 모나드까지. 명령형에서 함수형으로 사고 전환하기 위한 핵심 개념 정리.', source_type: 'NOTE', created_at: '2026-02-11T09:00:00Z', tags: ['프로그래밍', '함수형', 'FP'] },
  { id: 'dm-6', title: 'PostgreSQL 인덱스 전략과 쿼리 최적화', summary: 'B-Tree vs GIN vs GiST 인덱스 선택 기준, EXPLAIN ANALYZE 활용법, 실행 계획 읽는 법.', source_type: 'WEB', created_at: '2026-02-10T11:20:00Z', tags: ['데이터베이스', 'PostgreSQL', '최적화'] },
  { id: 'dm-7', title: '메타인지와 학습 효율의 관계', summary: '자신의 학습 과정을 모니터링하고 조절하는 메타인지 능력이 학습 효율을 크게 높인다는 연구 결과와 실천 방법.', source_type: 'PDF', created_at: '2026-02-09T13:30:00Z', tags: ['학습', '메타인지', '심리학'] },
  { id: 'dm-8', title: 'React Server Components 이해하기', summary: 'RSC가 기존 SSR과 다른 점, 서버/클라이언트 컴포넌트 경계, "use client" 지시어의 의미와 번들 사이즈 최적화 효과.', source_type: 'WEB', created_at: '2026-02-08T15:10:00Z', tags: ['React', '프론트엔드', 'RSC'] },
  { id: 'dm-9', title: '시간 관리 매트릭스: 긴급함 vs 중요함', summary: '아이젠하워 매트릭스를 실제 일과에 적용하는 방법. 2사분면(중요하지만 긴급하지 않은) 활동에 시간을 투자하는 것이 핵심.', source_type: 'NOTE', created_at: '2026-02-07T10:00:00Z', tags: ['생산성', '시간관리'] },
  { id: 'dm-10', title: 'LangGraph로 멀티 에이전트 워크플로우 구축하기', summary: 'LangGraph의 StateGraph 패턴으로 여러 AI 에이전트를 조합하는 방법. 조건부 라우팅, 상태 관리, 인간-인-더-루프 패턴.', source_type: 'WEB', created_at: '2026-02-06T09:30:00Z', tags: ['AI', 'LangGraph', '에이전트'] },
]

export const DEMO_MEMORY_DETAILS: Record<string, MemoryDetail> = {
  'dm-1': {
    id: 'dm-1',
    title: '트랜스포머 아키텍처의 핵심: Self-Attention 메커니즘',
    content: 'Self-Attention은 입력 시퀀스의 각 위치에서 다른 모든 위치와의 관계를 동시에 계산합니다.\n\n핵심 수식: Attention(Q, K, V) = softmax(QK^T / sqrt(d_k))V\n\n- Query, Key, Value 행렬로 변환 후 유사도 기반 가중 합산\n- Multi-Head Attention: 여러 attention head가 서로 다른 표현 부분공간 학습\n- Positional Encoding: 위치 정보를 사인/코사인 함수로 인코딩\n\nRNN 대비 장점:\n1. 병렬 처리 가능 (순차 의존성 없음)\n2. 장거리 의존성 직접 모델링\n3. 해석 가능한 attention 가중치',
    summary: 'Self-Attention이 시퀀스 내 모든 위치 간 관계를 동시에 계산하는 방식과, 이를 통해 RNN의 순차적 한계를 극복하는 원리를 정리.',
    source_url: 'https://example.com/transformer-attention',
    source_type: 'WEB',
    tags: ['AI', '딥러닝', 'Transformer'],
    created_at: '2026-02-15T10:30:00Z',
    updated_at: '2026-02-15T10:30:00Z',
  },
  'dm-2': {
    id: 'dm-2',
    title: '스토아 철학과 현대 인지행동치료의 연결',
    content: '에픽테토스: "우리를 괴롭히는 것은 사건 자체가 아니라 그에 대한 판단이다."\n\n이 핵심 사상이 CBT(인지행동치료)의 기반이 됨:\n- 자동적 사고(Automatic Thoughts) 인식\n- 인지 왜곡 패턴 식별\n- 합리적 대안 사고로 재구성\n\n마르쿠스 아우렐리우스의 명상록에서도 유사한 통찰:\n"사물 자체는 영혼을 건드리지 못한다. 사물은 영혼 바깥에 정지해 있다."\n\n현대적 적용:\n- 감정 일기 작성 → 사고-감정-행동 패턴 인식\n- 소크라테스식 질문법으로 인지 왜곡 검증\n- 가치 기반 행동 선택 (ACT와의 연결)',
    summary: '에픽테토스의 핵심 사상이 CBT의 인지 재구성과 직접 연결되는 점이 인상적.',
    source_url: 'https://example.com/stoic-cbt',
    source_type: 'WEB',
    tags: ['철학', '심리학', '스토아'],
    created_at: '2026-02-14T08:15:00Z',
    updated_at: '2026-02-14T08:15:00Z',
  },
  'dm-3': {
    id: 'dm-3',
    title: '개인 지식 관리(PKM) 시스템 설계 원칙',
    content: 'Zettelkasten 방식의 핵심은 하나의 노트에 하나의 아이디어만 담는 것.\n\n니클라스 루만의 원칙:\n1. 원자적 노트: 하나의 노트 = 하나의 아이디어\n2. 양방향 링크: 노트 간 연결이 새로운 통찰 생성\n3. 고유 식별자: 영구적 참조 가능한 ID 체계\n4. 색인: 진입점 역할의 구조 노트\n\n디지털 PKM 도구 비교:\n- Obsidian: 로컬 파일, 마크다운, 강력한 그래프 뷰\n- Notion: 클라우드, 데이터베이스 기반, 협업에 강점\n- Roam Research: 양방향 링크 선구자, 일일 노트 중심\n\n두 번째 뇌의 핵심: 수집이 아니라 연결. 정보를 모으는 것보다 정보 사이의 관계를 발견하는 것이 진정한 가치.',
    summary: 'Zettelkasten 방식의 원자적 노트 + 양방향 링크가 창의적 사고를 촉진하는 이유.',
    source_url: null,
    source_type: 'PDF',
    tags: ['PKM', '생산성', 'Zettelkasten'],
    created_at: '2026-02-13T14:00:00Z',
    updated_at: '2026-02-13T14:00:00Z',
  },
  'dm-4': {
    id: 'dm-4',
    title: '운동이 뇌에 미치는 영향: 신경과학적 근거',
    content: '규칙적 운동의 인지적 이점에 대한 과학적 근거:\n\n1. BDNF (Brain-Derived Neurotrophic Factor) 증가\n   - 뉴런 성장과 시냅스 가소성 촉진\n   - 유산소 운동 20분 후 혈중 BDNF 수치 상승\n\n2. 해마 뉴런 생성 (Neurogenesis)\n   - 해마 부피 1-2% 증가 (6개월 유산소 운동)\n   - 기억력과 공간 학습 능력 향상\n\n3. 전전두엽 기능 향상\n   - 실행 기능, 작업 기억, 주의 집중 개선\n   - 스트레스 호르몬(코르티솔) 조절\n\n권장 운동량: 주 150분 중강도 유산소 운동\n최적 타이밍: 학습 전 20-30분 운동이 기억 형성에 가장 효과적',
    summary: 'BDNF 증가, 해마 뉴런 생성, 전전두엽 기능 향상 등 규칙적 운동의 인지적 이점에 대한 최신 연구 정리.',
    source_url: 'https://example.com/exercise-brain',
    source_type: 'WEB',
    tags: ['건강', '뇌과학', '운동'],
    created_at: '2026-02-12T16:45:00Z',
    updated_at: '2026-02-12T16:45:00Z',
  },
  'dm-5': {
    id: 'dm-5',
    title: '함수형 프로그래밍의 핵심 개념 메모',
    content: '명령형에서 함수형으로 사고 전환하기 위한 핵심 개념:\n\n1. 불변성 (Immutability)\n   - 데이터를 변경하지 않고 새로운 데이터를 생성\n   - 부수 효과 제거, 예측 가능한 코드\n\n2. 순수 함수 (Pure Functions)\n   - 같은 입력 → 항상 같은 출력\n   - 외부 상태에 의존하지 않음\n\n3. 고차 함수 (Higher-Order Functions)\n   - map, filter, reduce로 선언적 데이터 변환\n   - 함수를 인자로 받거나 반환하는 함수\n\n4. 모나드 (Monad)\n   - 부수 효과를 타입 시스템으로 제어\n   - Maybe, Either, IO 등으로 안전한 합성\n\n실용적 팁: 작은 순수 함수부터 시작, 점진적으로 불변 패턴 도입',
    summary: '불변성, 순수 함수, 고차 함수, 모나드까지. 명령형에서 함수형으로 사고 전환하기 위한 핵심 개념 정리.',
    source_url: null,
    source_type: 'NOTE',
    tags: ['프로그래밍', '함수형', 'FP'],
    created_at: '2026-02-11T09:00:00Z',
    updated_at: '2026-02-11T09:00:00Z',
  },
  'dm-6': {
    id: 'dm-6',
    title: 'PostgreSQL 인덱스 전략과 쿼리 최적화',
    content: '인덱스 유형별 사용 기준:\n\n1. B-Tree (기본)\n   - 등호, 범위 검색에 최적\n   - 정렬된 데이터 접근, ORDER BY 최적화\n\n2. GIN (Generalized Inverted Index)\n   - 배열, JSONB, 전문 검색에 적합\n   - tsvector를 이용한 한국어 전문 검색\n\n3. GiST (Generalized Search Tree)\n   - 공간 데이터, 범위 타입\n   - PostGIS 지리 데이터 쿼리\n\nEXPLAIN ANALYZE 핵심 포인트:\n- Seq Scan vs Index Scan 비용 비교\n- Nested Loop vs Hash Join 선택 기준\n- work_mem 설정이 정렬 성능에 미치는 영향\n\npgvector 활용: 벡터 유사도 검색에 IVFFlat 또는 HNSW 인덱스 사용',
    summary: 'B-Tree vs GIN vs GiST 인덱스 선택 기준, EXPLAIN ANALYZE 활용법, 실행 계획 읽는 법.',
    source_url: 'https://example.com/pg-optimization',
    source_type: 'WEB',
    tags: ['데이터베이스', 'PostgreSQL', '최적화'],
    created_at: '2026-02-10T11:20:00Z',
    updated_at: '2026-02-10T11:20:00Z',
  },
  'dm-7': {
    id: 'dm-7',
    title: '메타인지와 학습 효율의 관계',
    content: '메타인지(Metacognition): "생각에 대한 생각"\n\n두 가지 핵심 요소:\n1. 메타인지 지식: 자신의 인지 능력과 한계에 대한 인식\n2. 메타인지 조절: 학습 전략의 계획, 모니터링, 평가\n\n효과적인 메타인지 전략:\n- 자기 질문법: "이 개념을 남에게 설명할 수 있나?"\n- 인출 연습: 텍스트를 덮고 기억해서 적기\n- 간격 반복: 잊어버리기 직전에 복습\n- 정교화: 새 정보를 기존 지식과 연결\n\n연구 결과: 메타인지 훈련을 받은 학생들의 학업 성취도가 평균 20% 향상\n\nUCL 연구: 메타인지 능력이 IQ보다 학업 성적을 더 잘 예측',
    summary: '자신의 학습 과정을 모니터링하고 조절하는 메타인지 능력이 학습 효율을 크게 높인다는 연구 결과와 실천 방법.',
    source_url: null,
    source_type: 'PDF',
    tags: ['학습', '메타인지', '심리학'],
    created_at: '2026-02-09T13:30:00Z',
    updated_at: '2026-02-09T13:30:00Z',
  },
  'dm-8': {
    id: 'dm-8',
    title: 'React Server Components 이해하기',
    content: 'RSC(React Server Components)의 핵심:\n\n서버 컴포넌트 vs 클라이언트 컴포넌트:\n- 서버 컴포넌트: DB 직접 접근, 번들에 미포함, 상호작용 불가\n- 클라이언트 컴포넌트: "use client" 선언, 상태/이벤트 처리 가능\n\n기존 SSR과의 차이:\n- SSR: 전체 페이지를 서버에서 HTML로 렌더링\n- RSC: 컴포넌트 단위로 서버/클라이언트 분리\n\n번들 사이즈 최적화:\n- moment.js 같은 무거운 라이브러리를 서버 컴포넌트에서만 사용\n- 클라이언트 번들에서 제외되어 로딩 속도 향상\n\n데이터 페칭 패턴:\n- 서버 컴포넌트에서 async/await로 직접 데이터 로드\n- Suspense와 결합하여 스트리밍 렌더링 가능',
    summary: 'RSC가 기존 SSR과 다른 점, 서버/클라이언트 컴포넌트 경계의 의미와 번들 사이즈 최적화 효과.',
    source_url: 'https://example.com/react-rsc',
    source_type: 'WEB',
    tags: ['React', '프론트엔드', 'RSC'],
    created_at: '2026-02-08T15:10:00Z',
    updated_at: '2026-02-08T15:10:00Z',
  },
  'dm-9': {
    id: 'dm-9',
    title: '시간 관리 매트릭스: 긴급함 vs 중요함',
    content: '아이젠하워 매트릭스:\n\n| | 긴급 | 비긴급 |\n|---|---|---|\n| 중요 | 1사분면: 즉시 처리 | 2사분면: 계획적 투자 |\n| 비중요 | 3사분면: 위임 | 4사분면: 제거 |\n\n핵심 통찰: 2사분면에 시간을 투자하면 1사분면의 위기가 줄어듦\n\n2사분면 활동 예시:\n- 장기 프로젝트 계획\n- 건강 관리 (운동, 식단)\n- 인간관계 구축\n- 자기 개발과 학습\n- 시스템/프로세스 구축\n\n실천 방법:\n1. 주간 계획에서 2사분면 활동을 먼저 블록\n2. "아니오"라고 말하는 연습 (3사분면 줄이기)\n3. 디지털 디톡스로 4사분면 최소화\n4. 주간 회고로 시간 사용 패턴 분석',
    summary: '아이젠하워 매트릭스를 실제 일과에 적용하는 방법. 2사분면 활동에 시간을 투자하는 것이 핵심.',
    source_url: null,
    source_type: 'NOTE',
    tags: ['생산성', '시간관리'],
    created_at: '2026-02-07T10:00:00Z',
    updated_at: '2026-02-07T10:00:00Z',
  },
  'dm-10': {
    id: 'dm-10',
    title: 'LangGraph로 멀티 에이전트 워크플로우 구축하기',
    content: 'LangGraph: LangChain 기반 멀티 에이전트 프레임워크\n\n핵심 개념:\n1. StateGraph: 상태 기반 그래프로 에이전트 워크플로우 정의\n2. Node: 각 에이전트 또는 처리 단계\n3. Edge: 노드 간 전이 (조건부 라우팅 가능)\n4. State: TypedDict로 정의된 공유 상태\n\n조건부 라우팅:\n- 이전 노드의 출력에 따라 다음 노드 결정\n- should_continue() 함수로 분기 로직 구현\n\n인간-인-더-루프 (HITL):\n- interrupt_before/interrupt_after로 실행 일시 중지\n- 사용자 확인 후 재개\n- 중요한 결정에 인간 개입 보장\n\n실전 패턴:\n- Supervisor 에이전트가 하위 에이전트들을 조율\n- 각 에이전트는 독립적 도구와 프롬프트 보유\n- 상태를 통한 정보 공유와 협업',
    summary: 'LangGraph의 StateGraph 패턴으로 여러 AI 에이전트를 조합하는 방법. 조건부 라우팅, 상태 관리, 인간-인-더-루프 패턴.',
    source_url: 'https://example.com/langgraph-multi-agent',
    source_type: 'WEB',
    tags: ['AI', 'LangGraph', '에이전트'],
    created_at: '2026-02-06T09:30:00Z',
    updated_at: '2026-02-06T09:30:00Z',
  },
}

// ─── 채팅 ──────────────────────────────────────────────────────────────────

export const DEMO_SESSIONS: ChatSessionResponse[] = [
  { id: 'ds-1', title: 'AI 에이전트의 미래에 대해', created_at: '2026-02-15T11:00:00Z' },
  { id: 'ds-2', title: '효과적인 학습법 토론', created_at: '2026-02-13T09:00:00Z' },
  { id: 'ds-3', title: '함수형 프로그래밍 심화 질문', created_at: '2026-02-11T14:00:00Z' },
]

export const DEMO_CHAT_MESSAGES: Record<string, ChatMessage[]> = {
  'ds-1': [
    { role: 'user', content: 'LangGraph로 멀티 에이전트 시스템을 만들 때 가장 중요한 설계 원칙이 뭘까?' },
    { role: 'assistant', content: '좋은 질문이에요! 저장하신 LangGraph 관련 메모리를 보면, StateGraph 패턴과 조건부 라우팅에 대해 정리하셨더라구요.\n\n멀티 에이전트 설계에서 가장 중요한 원칙은 **각 에이전트의 책임을 명확히 분리**하는 것입니다. 예를 들어:\n\n1. **단일 책임**: 각 에이전트는 하나의 역할만 수행\n2. **명시적 상태 관리**: 에이전트 간 공유 상태를 TypedDict로 정의\n3. **인간-인-더-루프**: 중요한 결정 지점에 사람이 개입할 수 있는 구조\n\n혹시 트랜스포머 아키텍처에 대해 정리하신 내용과 연결해서, 에이전트의 attention 메커니즘에 대해서도 생각해보신 적 있으신가요?', references: [{ id: 'dm-10', title: 'LangGraph로 멀티 에이전트 워크플로우 구축하기', source_type: 'WEB', created_at: '2026-02-06' }] },
    { role: 'user', content: '오, 트랜스포머랑 에이전트를 연결하는 관점은 생각 못 했는데 흥미롭다!' },
    { role: 'assistant', content: '맞아요! 실은 둘 다 "어디에 주의를 기울일 것인가"라는 같은 문제를 다루고 있거든요.\n\nSelf-Attention이 시퀀스 내에서 관련 정보를 찾듯이, 멀티 에이전트 시스템에서도 각 에이전트가 전체 상태에서 자신에게 관련된 정보만 "attend"하는 게 효율적이에요.\n\n이런 관점에서 보면, 저장하신 트랜스포머 아키텍처 메모리의 핵심 인사이트가 에이전트 설계에도 적용될 수 있습니다. 기억들 사이에 이런 숨겨진 연결을 발견하는 게 바로 Memoir의 가치죠!' },
  ],
  'ds-2': [
    { role: 'user', content: '메타인지와 학습 효율에 대해 정리한 게 있는데, 실제로 어떻게 적용하면 좋을까?' },
    { role: 'assistant', content: '메타인지 관련 PDF에서 정리하신 내용을 보면, 자기 모니터링과 자기 조절 두 가지가 핵심이었죠.\n\n실제 적용 방법을 제안드려볼게요:\n\n**학습 전**: "이 주제에 대해 이미 아는 것은?" → 사전 지식 활성화\n**학습 중**: 주기적으로 "지금까지 이해한 것을 요약해볼까?" → 이해도 모니터링\n**학습 후**: "가장 헷갈리는 부분은?" → 약점 파악 및 집중 복습\n\n흥미로운 점은, 스토아 철학에서 정리하신 "판단에 대한 판단" 개념이 메타인지와 매우 유사하다는 거예요. 에픽테토스가 말한 것처럼, 자신의 사고 과정을 관찰하는 능력이 핵심입니다.', references: [{ id: 'dm-7', title: '메타인지와 학습 효율의 관계', source_type: 'PDF', created_at: '2026-02-09' }, { id: 'dm-2', title: '스토아 철학과 현대 인지행동치료의 연결', source_type: 'WEB', created_at: '2026-02-14' }] },
  ],
  'ds-3': [
    { role: 'user', content: '함수형 프로그래밍에서 모나드가 정확히 뭐야? 쉽게 설명해줘.' },
    { role: 'assistant', content: '함수형 프로그래밍 메모에서 모나드를 정리하셨는데, 좀 더 직관적으로 설명해볼게요.\n\n모나드는 **"값을 감싸는 컨텍스트"**라고 생각하면 됩니다:\n\n- **Maybe 모나드**: 값이 있을 수도 없을 수도 있는 컨텍스트\n  - `Maybe(42)` → 값이 있음\n  - `Maybe(null)` → 값이 없음\n  - null 체크를 자동으로 처리\n\n- **Either 모나드**: 성공 또는 실패 컨텍스트\n  - `Right(result)` → 성공\n  - `Left(error)` → 실패\n  - try-catch 없이 에러 전파\n\n핵심은 **합성(composition)**이에요. 모나드끼리 체이닝하면 부수 효과를 깔끔하게 관리하면서도 타입 안전성을 유지할 수 있습니다.\n\nPostgreSQL 최적화에서 정리하신 쿼리 파이프라인도 사실 모나드적 사고와 유사해요. 각 단계가 독립적이면서도 순서대로 합성되는 패턴이거든요.', references: [{ id: 'dm-5', title: '함수형 프로그래밍의 핵심 개념 메모', source_type: 'NOTE', created_at: '2026-02-11' }] },
  ],
}

// SSE 스트리밍 시뮬레이션용 응답 데이터
export interface DemoChatResponse {
  keywords: string[]
  content: string
  references: ChatReference[]
}

export const DEMO_CHAT_RESPONSES: DemoChatResponse[] = [
  {
    keywords: ['오늘', '하루', '기분', '어때'],
    content: '오늘 하루는 어떠셨나요? 저장하신 기억들을 보면 최근 AI와 인문학의 교차점에 대해 많이 탐구하고 계신 것 같아요.\n\n혹시 오늘 새롭게 배운 것이나 인상 깊었던 경험이 있으시다면 나눠주세요. 기존 기억들과 연결해서 흥미로운 통찰을 찾아볼 수 있을 거예요.\n\n참고로, 시간 관리에 대해 정리하신 아이젠하워 매트릭스를 오늘 일과에 적용해보신 적 있나요?',
    references: [{ id: 'dm-9', title: '시간 관리 매트릭스: 긴급함 vs 중요함', source_type: 'NOTE', created_at: '2026-02-07' }],
  },
  {
    keywords: ['관심사', '최근', '요즘', '뭐'],
    content: '최근 저장하신 기억들의 패턴을 분석해보면, 크게 두 가지 흐름이 보여요:\n\n1. **기술 심화**: AI/딥러닝, 함수형 프로그래밍, 데이터베이스 최적화\n2. **인문학적 성찰**: 스토아 철학, 메타인지, PKM 시스템\n\n흥미로운 점은 이 두 흐름이 "체계적 사고"라는 공통 주제로 연결된다는 거예요. 트랜스포머의 Self-Attention도, 스토아의 자기 성찰도, 결국 "무엇에 주의를 기울일 것인가"에 대한 탐구니까요.\n\n이 연결에 대해 더 깊이 생각해보고 싶으신 부분이 있으신가요?',
    references: [
      { id: 'dm-1', title: '트랜스포머 아키텍처의 핵심: Self-Attention 메커니즘', source_type: 'WEB', created_at: '2026-02-15' },
      { id: 'dm-2', title: '스토아 철학과 현대 인지행동치료의 연결', source_type: 'WEB', created_at: '2026-02-14' },
    ],
  },
  {
    keywords: ['저장', '글', '인상적', '읽', '메모'],
    content: '네, 기억 저장과 관련해서 좋은 습관을 가지고 계시네요! PKM 시스템에 대해 정리하신 내용을 보면, Zettelkasten의 원자적 노트 원칙을 알고 계시잖아요.\n\n효과적인 기억 저장 팁을 드리자면:\n\n1. **핵심 인사이트 한 줄**: 글에서 가장 인상 깊었던 한 문장을 요약\n2. **나만의 해석 추가**: "이것이 나에게 의미하는 것은..."\n3. **기존 기억과 연결**: "이것은 저번에 정리한 X와 관련이 있다"\n\n이렇게 하면 Memoir이 기억들 사이의 연결을 더 잘 발견할 수 있어요. 실제로 함수형 프로그래밍과 스토아 철학의 연결처럼, 의외의 통찰이 생기곤 합니다!',
    references: [{ id: 'dm-3', title: '개인 지식 관리(PKM) 시스템 설계 원칙', source_type: 'PDF', created_at: '2026-02-13' }],
  },
  {
    keywords: ['학습', '공부', '배우', '효율'],
    content: '학습 효율에 대해 물어봐주셨네요! 메타인지 관련 메모리와 운동-뇌 건강 메모리에서 정리하신 내용을 결합하면 최적의 학습 전략을 세울 수 있어요.\n\n**과학적 근거 기반 학습법:**\n\n1. **운동 → 학습**: 20분 유산소 운동 후 BDNF 증가로 기억 형성 촉진\n2. **메타인지적 모니터링**: "이해했나?" 대신 "설명할 수 있나?" 자문\n3. **간격 반복**: 잊어버리기 직전에 복습 (최적 간격: 1일 → 3일 → 7일 → 21일)\n4. **인터리빙**: 한 주제만 몰아서 하지 않고 여러 주제를 섞어 학습\n\n시간 관리 매트릭스에서 정리하신 것처럼, 학습은 2사분면(중요하지만 긴급하지 않은) 활동이에요. 의도적으로 시간을 확보해야 합니다.',
    references: [
      { id: 'dm-7', title: '메타인지와 학습 효율의 관계', source_type: 'PDF', created_at: '2026-02-09' },
      { id: 'dm-4', title: '운동이 뇌에 미치는 영향: 신경과학적 근거', source_type: 'WEB', created_at: '2026-02-12' },
    ],
  },
  {
    keywords: ['건강', '운동', '몸', '체력'],
    content: '운동과 건강에 대해 관심이 있으시군요! 뇌과학 관련 메모리에서 정리하신 내용이 도움이 될 거예요.\n\n핵심 포인트를 상기해드리면:\n\n- **BDNF 효과**: 유산소 운동 20분 후 뇌의 성장인자 증가\n- **해마 신경 생성**: 6개월 규칙적 운동으로 해마 부피 1-2% 증가\n- **최적 타이밍**: 학습 전 20-30분 운동이 기억 형성에 가장 효과적\n\n스토아 철학에서 배운 "통제할 수 있는 것에 집중하라"는 원칙을 운동에도 적용해보세요. 날씨, 컨디션은 통제할 수 없지만, 운동화를 신고 문 밖으로 나가는 것은 통제할 수 있으니까요.\n\n오늘 운동은 하셨나요?',
    references: [
      { id: 'dm-4', title: '운동이 뇌에 미치는 영향: 신경과학적 근거', source_type: 'WEB', created_at: '2026-02-12' },
      { id: 'dm-2', title: '스토아 철학과 현대 인지행동치료의 연결', source_type: 'WEB', created_at: '2026-02-14' },
    ],
  },
]

// ─── 저널 ──────────────────────────────────────────────────────────────────

export const DEMO_JOURNAL_DATES = [
  '2026-02-21', '2026-02-20', '2026-02-18', '2026-02-17', '2026-02-15', '2026-02-13', '2026-02-10',
]

export interface DemoJournal {
  id: string
  date: string
  content: string
  mood: string
}

export const DEMO_JOURNALS: Record<string, DemoJournal> = {
  '2026-02-21': { id: 'dj-0', date: '2026-02-21', content: '오늘 Memoir을 데모 모드로 체험해보고 있다. 기억을 체계적으로 정리하고 연결하는 이 시스템이 정말 흥미롭다.\n\n개인 지식 관리(PKM)에 대해 정리했던 Zettelkasten 원칙이 여기서 실현되는 느낌. 단순히 정보를 저장하는 것이 아니라, 정보 사이의 관계를 발견하는 것이 핵심이라는 점이 와닿는다.', mood: '💡' },
  '2026-02-20': { id: 'dj-4', date: '2026-02-20', content: '아이젠하워 매트릭스를 실제로 오늘 일과에 적용해봤다. 확실히 2사분면 활동을 의식적으로 먼저 블록하니까 긴급한 일에 휘둘리는 느낌이 줄었다.\n\n메타인지적으로도 좋은 경험이었다. 자신의 시간 사용 패턴을 관찰하는 것 자체가 행동 변화를 만든다는 것을 체감.', mood: '✅' },
  '2026-02-18': { id: 'dj-1', date: '2026-02-18', content: '오늘 트랜스포머와 멀티 에이전트 시스템의 연결고리를 발견했다. Self-Attention과 에이전트의 상태 관리가 결국 같은 문제를 다른 스케일에서 풀고 있다는 점이 흥미롭다.\n\nMemoir을 쓰면서 이런 연결을 자연스럽게 발견하게 되는 것 같다. 기억을 체계적으로 정리하면 새로운 통찰이 생기는 경험.', mood: '🧠' },
  '2026-02-17': { id: 'dj-2', date: '2026-02-17', content: '주말에 함수형 프로그래밍 관련 메모를 다시 읽어봤다. 불변성의 원칙이 단순히 코딩 스타일이 아니라 사고의 명확성과도 연결된다는 생각.\n\n스토아 철학에서 말하는 "통제할 수 있는 것과 없는 것의 구분"이 순수 함수의 부작용 없는 설계와 비슷하다.', mood: '💡' },
  '2026-02-15': { id: 'dj-3', date: '2026-02-15', content: '오늘 아침 조깅을 하면서 BDNF와 뇌 건강에 대해 생각했다. 운동 후에 확실히 머리가 맑아지는 느낌이 드는데, 이게 과학적으로 입증된 현상이라니.\n\n운동→BDNF 증가→해마 뉴런 생성→학습 능력 향상의 선순환을 만들어가자.', mood: '🏃' },
  '2026-02-13': { id: 'dj-5', date: '2026-02-13', content: 'PKM 시스템에 대한 논문을 읽고 정리했다. Zettelkasten 방식이 왜 효과적인지 이론적 배경을 이해하게 됐다.\n\n핵심은 "수집이 아니라 연결"이라는 것. 많은 사람들이 정보를 모으는 데 집중하지만, 정보 사이의 관계를 발견하는 것이 진정한 지식 구축이다.', mood: '📚' },
  '2026-02-10': { id: 'dj-6', date: '2026-02-10', content: 'PostgreSQL 인덱스 최적화에 대해 깊이 있게 공부했다. pgvector의 HNSW 인덱스가 특히 인상적.\n\n기술적 깊이와 실용성 사이의 균형을 찾는 것이 중요하다는 생각이 든다. 너무 이론에만 빠지지 말고, 실제 프로젝트에 적용해보자.', mood: '💻' },
}

export const DEMO_JOURNAL_ENTRIES: Record<string, JournalEntry> = Object.fromEntries(
  Object.entries(DEMO_JOURNALS).map(([date, j]) => [
    date,
    {
      id: j.id,
      content: j.content,
      mood: j.mood,
      created_at: `${date}T09:00:00Z`,
      updated_at: `${date}T09:00:00Z`,
    },
  ])
)

export const DEMO_JOURNAL_ANALYSIS: InsightsResponse = {
  has_distortions: false,
  distortions: [],
  wellness_score: 82,
}

export const DEMO_REVIEW_QUESTIONS: ReviewQuestionsResponse = {
  questions: [
    '오늘 가장 인상 깊었던 학습 내용은 무엇인가요?',
    '최근 발견한 기억들 사이의 연결 중에서 가장 흥미로운 것은?',
    '내일 가장 우선적으로 하고 싶은 2사분면 활동은 무엇인가요?',
  ],
}

export const DEMO_RELATED_MEMORIES: RelatedMemoriesResponse = {
  memories: [
    { id: 'dm-3', title: '개인 지식 관리(PKM) 시스템 설계 원칙', summary: 'Zettelkasten 방식의 원자적 노트 + 양방향 링크가 창의적 사고를 촉진하는 이유.', type: 'semantic', created_at: '2026-02-13T14:00:00Z', similarity: 0.89 },
    { id: 'dm-7', title: '메타인지와 학습 효율의 관계', summary: '자신의 학습 과정을 모니터링하고 조절하는 메타인지 능력이 학습 효율을 크게 높인다.', type: 'semantic', created_at: '2026-02-09T13:30:00Z', similarity: 0.82 },
    { id: 'dm-9', title: '시간 관리 매트릭스: 긴급함 vs 중요함', summary: '아이젠하워 매트릭스를 실제 일과에 적용하는 방법.', type: 'keyword', created_at: '2026-02-07T10:00:00Z', similarity: 0.75 },
  ],
}

// ─── 대시보드 ──────────────────────────────────────────────────────────────

export const DEMO_BRIEFING: BriefingData = {
  today_memories: { count: 2, topics: ['AI', '철학'] },
  unreviewed_count: 3,
  streak: { current: 5, longest: 12 },
  suggested_question: '트랜스포머의 Self-Attention과 인간의 선택적 주의력은 어떤 점에서 비슷하고 다를까요?',
  connection_hint: '"함수형 프로그래밍"과 "스토아 철학" 사이에 흥미로운 연결이 있을 수 있어요.',
}

export const DEMO_STREAK: StreakData = {
  current_streak: 5,
  longest_streak: 12,
  total_active_days: 28,
  last_active_date: '2026-02-18',
}

export const DEMO_STATS: StatsData = {
  overview: { total_memories: 42, total_this_week: 5, total_this_month: 18, most_active_day: '월요일' },
  recent_activity: [],
  sources: [
    { source_type: 'WEB', count: 25, percentage: 59.5 },
    { source_type: 'NOTE', count: 10, percentage: 23.8 },
    { source_type: 'PDF', count: 7, percentage: 16.7 },
  ],
  top_tags: [
    { tag: 'AI', count: 12 }, { tag: '프로그래밍', count: 9 },
    { tag: '심리학', count: 7 }, { tag: '생산성', count: 6 },
    { tag: '철학', count: 5 }, { tag: '건강', count: 4 },
  ],
}

const today = new Date()
export const DEMO_ACTIVITY: ActivityData[] = Array.from({ length: 60 }, (_, i) => {
  const d = new Date(today)
  d.setDate(d.getDate() - (59 - i))
  return { date: d.toISOString().slice(0, 10), count: Math.floor(Math.random() * 5) }
})

export const DEMO_INSIGHTS: DailyInsight[] = [
  { type: 'pattern', icon: '🔄', title: 'AI와 인문학의 교차', description: '최근 AI 기술과 철학/심리학을 연결하는 메모리가 증가하고 있어요. 학제적 사고가 돋보입니다!', cta_label: '관련 메모리 보기', cta_path: '/demo/memories' },
  { type: 'connection', icon: '🔗', title: '숨겨진 연결 발견', description: '"메타인지"와 "함수형 프로그래밍"이 "자기 관찰"이라는 공통 주제로 연결될 수 있어요.', cta_label: '그래프에서 확인', cta_path: '/demo/graph' },
  { type: 'action', icon: '✍️', title: '오늘의 회고 시간', description: '3일 연속 새로운 메모리를 저장하셨네요! 오늘의 학습을 저널로 정리해보세요.', cta_label: '저널 쓰기', cta_path: '/demo/journal' },
]

export const DEMO_DIGEST: DigestData = {
  date: new Date().toISOString().slice(0, 10),
  summary: {
    memory_count: 3,
    journal_count: 1,
    chat_count: 2,
  },
  memories: [
    { id: 'dm-1', title: '트랜스포머 아키텍처의 핵심: Self-Attention 메커니즘', type: 'WEB', summary: 'Self-Attention 메커니즘의 원리와 RNN 대비 장점 정리', tags: ['AI', '딥러닝', 'Transformer'] },
    { id: 'dm-2', title: '스토아 철학과 현대 인지행동치료의 연결', type: 'WEB', summary: '에픽테토스의 사상과 CBT의 인지 재구성 연결', tags: ['철학', '심리학', '스토아'] },
    { id: 'dm-3', title: '개인 지식 관리(PKM) 시스템 설계 원칙', type: 'PDF', summary: 'Zettelkasten 원자적 노트 원칙과 양방향 링크', tags: ['PKM', '생산성', 'Zettelkasten'] },
  ],
  journals: [
    { id: 'dj-1', mood: '🧠', preview: '오늘 트랜스포머와 멀티 에이전트 시스템의 연결고리를 발견했다...', created_at: '2026-02-18T09:00:00Z' },
  ],
  chats: [],
  insights: {
    main_topics: ['AI', '철학', 'PKM'],
    suggested_questions: [
      '트랜스포머의 Self-Attention과 스토아 철학의 자기 성찰 사이에 구조적 유사성이 있을까요?',
      'Zettelkasten 방식을 AI 에이전트 설계에 적용할 수 있는 방법은?',
    ],
  },
}

export const DEMO_WEEKLY_REPORT: ReportData = {
  period: 'weekly',
  date_range: '2026-02-15 ~ 2026-02-21',
  total_memories: 5,
  total_journals: 4,
  topic_distribution: [
    { topic: 'AI/딥러닝', count: 3, percentage: 30 },
    { topic: '철학/심리학', count: 3, percentage: 30 },
    { topic: '프로그래밍', count: 2, percentage: 20 },
    { topic: '생산성', count: 2, percentage: 20 },
  ],
  source_distribution: [
    { source_type: 'WEB', count: 3, percentage: 60 },
    { source_type: 'NOTE', count: 1, percentage: 20 },
    { source_type: 'PDF', count: 1, percentage: 20 },
  ],
  llm_summary: '이번 주에는 AI 기술(트랜스포머, LangGraph)과 인문학적 성찰(스토아 철학, 메타인지)을 연결하는 학제적 탐구가 돋보였습니다. 특히 Self-Attention 메커니즘과 에이전트 설계 사이의 연결점을 발견한 것이 주목할 만합니다. PKM 시스템에 대한 깊은 이해가 전반적인 지식 관리 품질을 높이고 있습니다.',
  highlights: [
    '트랜스포머와 멀티 에이전트 시스템의 구조적 유사성 발견',
    '스토아 철학의 원칙을 함수형 프로그래밍과 연결하는 새로운 관점',
    '메타인지 전략의 실제 학습 적용 계획 수립',
    '5일 연속 활동 — 꾸준한 지식 축적 습관 형성 중',
  ],
}

export const DEMO_MONTHLY_REPORT: ReportData = {
  period: 'monthly',
  date_range: '2026-02-01 ~ 2026-02-21',
  total_memories: 18,
  total_journals: 7,
  topic_distribution: [
    { topic: 'AI/딥러닝', count: 6, percentage: 33 },
    { topic: '철학/심리학', count: 4, percentage: 22 },
    { topic: '프로그래밍', count: 4, percentage: 22 },
    { topic: '생산성/학습', count: 3, percentage: 17 },
    { topic: '건강', count: 1, percentage: 6 },
  ],
  source_distribution: [
    { source_type: 'WEB', count: 11, percentage: 61 },
    { source_type: 'NOTE', count: 4, percentage: 22 },
    { source_type: 'PDF', count: 3, percentage: 17 },
  ],
  llm_summary: '2월에는 총 18개의 기억을 저장하고 7개의 저널을 작성하셨습니다. AI 기술과 인문학적 사고를 연결하는 학제적 탐구가 이번 달의 핵심 테마였습니다. 특히 "주의(Attention)"라는 개념이 트랜스포머 아키텍처, 스토아 철학, 메타인지를 관통하는 공통 주제로 부상했습니다. 꾸준한 저널 작성을 통해 학습 경험을 체계적으로 성찰하는 습관이 강화되고 있습니다.',
  highlights: [
    'AI와 인문학을 연결하는 독창적 관점 형성',
    '"주의(Attention)"를 관통 키워드로 한 지식 네트워크 구축',
    '월 18개 메모리 저장 — 적극적 지식 수집 활동',
    'Zettelkasten + Memoir으로 실질적 두 번째 뇌 구축 진행 중',
    '운동-뇌 건강-학습 효율의 선순환 인식과 실천',
  ],
}

// ─── 타임라인 ──────────────────────────────────────────────────────────────

export const DEMO_TIMELINE: TimelineGroup[] = [
  {
    date: '2026-02-15',
    memories: [DEMO_MEMORIES[0]],
  },
  {
    date: '2026-02-14',
    memories: [DEMO_MEMORIES[1]],
  },
  {
    date: '2026-02-13',
    memories: [DEMO_MEMORIES[2]],
  },
  {
    date: '2026-02-12',
    memories: [DEMO_MEMORIES[3]],
  },
  {
    date: '2026-02-11',
    memories: [DEMO_MEMORIES[4]],
  },
  {
    date: '2026-02-10',
    memories: [DEMO_MEMORIES[5]],
  },
  {
    date: '2026-02-09',
    memories: [DEMO_MEMORIES[6]],
  },
  {
    date: '2026-02-08',
    memories: [DEMO_MEMORIES[7]],
  },
  {
    date: '2026-02-07',
    memories: [DEMO_MEMORIES[8]],
  },
  {
    date: '2026-02-06',
    memories: [DEMO_MEMORIES[9]],
  },
]

// ─── 그래프 ──────────────────────────────────────────────────────────────

export const DEMO_GRAPH: GraphData = {
  nodes: [
    { id: 'e-ai', label: 'AI', group: 'Topic', properties: { name: 'AI' }, val: 12 },
    { id: 'e-dl', label: '딥러닝', group: 'Topic', properties: { name: '딥러닝' }, val: 6 },
    { id: 'e-tf', label: 'Transformer', group: 'Topic', properties: { name: 'Transformer' }, val: 5 },
    { id: 'e-lg', label: 'LangGraph', group: 'Topic', properties: { name: 'LangGraph' }, val: 4 },
    { id: 'e-fp', label: '함수형 프로그래밍', group: 'Topic', properties: { name: '함수형 프로그래밍' }, val: 5 },
    { id: 'e-ph', label: '철학', group: 'Topic', properties: { name: '철학' }, val: 5 },
    { id: 'e-st', label: '스토아', group: 'Topic', properties: { name: '스토아' }, val: 4 },
    { id: 'e-ps', label: '심리학', group: 'Topic', properties: { name: '심리학' }, val: 7 },
    { id: 'e-mc', label: '메타인지', group: 'Concept', properties: { name: '메타인지' }, val: 5 },
    { id: 'e-cbt', label: 'CBT', group: 'Concept', properties: { name: 'CBT' }, val: 3 },
    { id: 'e-pkm', label: 'PKM', group: 'Topic', properties: { name: 'PKM' }, val: 4 },
    { id: 'e-zk', label: 'Zettelkasten', group: 'Concept', properties: { name: 'Zettelkasten' }, val: 3 },
    { id: 'e-br', label: '뇌과학', group: 'Topic', properties: { name: '뇌과학' }, val: 4 },
    { id: 'e-ex', label: '운동', group: 'Topic', properties: { name: '운동' }, val: 3 },
    { id: 'e-pg', label: 'PostgreSQL', group: 'Topic', properties: { name: 'PostgreSQL' }, val: 3 },
    { id: 'e-rc', label: 'React', group: 'Topic', properties: { name: 'React' }, val: 4 },
  ],
  links: [
    { source: 'e-ai', target: 'e-dl', type: 'RELATED_TO' },
    { source: 'e-dl', target: 'e-tf', type: 'INCLUDES' },
    { source: 'e-ai', target: 'e-lg', type: 'RELATED_TO' },
    { source: 'e-ph', target: 'e-st', type: 'INCLUDES' },
    { source: 'e-st', target: 'e-cbt', type: 'INFLUENCED' },
    { source: 'e-ps', target: 'e-cbt', type: 'INCLUDES' },
    { source: 'e-ps', target: 'e-mc', type: 'RELATED_TO' },
    { source: 'e-mc', target: 'e-pkm', type: 'RELATED_TO' },
    { source: 'e-pkm', target: 'e-zk', type: 'INCLUDES' },
    { source: 'e-br', target: 'e-ex', type: 'RELATED_TO' },
    { source: 'e-br', target: 'e-ps', type: 'RELATED_TO' },
    { source: 'e-fp', target: 'e-ph', type: 'INSPIRED_BY' },
    { source: 'e-ai', target: 'e-rc', type: 'RELATED_TO' },
    { source: 'e-pg', target: 'e-ai', type: 'USED_BY' },
  ],
}

export const DEMO_GRAPH_INSIGHTS: GraphInsights = {
  clusters: [
    { cluster_id: 0, entities: ['AI', '딥러닝', 'Transformer', 'LangGraph'], entity_types: ['Topic', 'Topic', 'Topic', 'Topic'], size: 4, summary: 'AI/딥러닝 기술 클러스터' },
    { cluster_id: 1, entities: ['철학', '스토아', '심리학', 'CBT', '메타인지'], entity_types: ['Topic', 'Topic', 'Topic', 'Concept', 'Concept'], size: 5, summary: '인문학/심리학 클러스터' },
  ],
  trends: [
    { tag: 'AI', counts: [3, 5, 7, 12], direction: 'up' },
    { tag: '심리학', counts: [2, 4, 5, 7], direction: 'up' },
  ],
  isolated_nodes: [],
  hub_nodes: [
    { name: 'AI', type: 'Topic', degree: 5 },
    { name: '심리학', type: 'Topic', degree: 4 },
  ],
}
