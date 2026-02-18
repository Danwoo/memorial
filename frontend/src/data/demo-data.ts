import type { Memory, MemoryDetail } from '../types/memory'
import type { ChatMessage, ChatSessionResponse } from '../types/chat'
import type { BriefingData, StatsData, StreakData, ActivityData, DailyInsight } from '../types/dashboard'
import type { GraphData, GraphInsights } from '../types/graph'

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
  'dm-1': { id: 'dm-1', title: 'トランスフォーマー 아키텍처의 핵심: Self-Attention 메커니즘', content: 'Self-Attention은 입력 시퀀스의 각 위치에서 다른 모든 위치와의 관계를 동시에 계산합니다...', summary: 'Self-Attention이 시퀀스 내 모든 위치 간 관계를 동시에 계산하는 방식.', source_url: 'https://example.com/transformer', source_type: 'WEB', tags: ['AI', '딥러닝', 'Transformer'], created_at: '2026-02-15T10:30:00Z', updated_at: '2026-02-15T10:30:00Z' },
  'dm-3': { id: 'dm-3', title: '개인 지식 관리(PKM) 시스템 설계 원칙', content: 'Zettelkasten 방식의 핵심은 하나의 노트에 하나의 아이디어만 담는 것...', summary: 'Zettelkasten 방식의 원자적 노트 + 양방향 링크.', source_url: null, source_type: 'PDF', tags: ['PKM', '생산성', 'Zettelkasten'], created_at: '2026-02-13T14:00:00Z', updated_at: '2026-02-13T14:00:00Z' },
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
    { role: 'assistant', content: '맞아요! 실은 둘 다 "어디에 주의를 기울일 것인가"라는 같은 문제를 다루고 있거든요.\n\nSelf-Attention이 시퀀스 내에서 관련 정보를 찾듯이, 멀티 에이전트 시스템에서도 각 에이전트가 전체 상태에서 자신에게 관련된 정보만 "attend"하는 게 효율적이에요.\n\n이런 관점에서 보면, 저장하신 트랜스포머 아키텍처 메모리의 핵심 인사이트가 에이전트 설계에도 적용될 수 있습니다. 기억들 사이에 이런 숨겨진 연결을 발견하는 게 바로 Memoir의 가치죠! 😊' },
  ],
  'ds-2': [
    { role: 'user', content: '메타인지와 학습 효율에 대해 정리한 게 있는데, 실제로 어떻게 적용하면 좋을까?' },
    { role: 'assistant', content: '메타인지 관련 PDF에서 정리하신 내용을 보면, 자기 모니터링과 자기 조절 두 가지가 핵심이었죠.\n\n실제 적용 방법을 제안드려볼게요:\n\n**학습 전**: "이 주제에 대해 이미 아는 것은?" → 사전 지식 활성화\n**학습 중**: 주기적으로 "지금까지 이해한 것을 요약해볼까?" → 이해도 모니터링\n**학습 후**: "가장 헷갈리는 부분은?" → 약점 파악 및 집중 복습\n\n흥미로운 점은, 스토아 철학에서 정리하신 "판단에 대한 판단" 개념이 메타인지와 매우 유사하다는 거예요. 에픽테토스가 말한 것처럼, 자신의 사고 과정을 관찰하는 능력이 핵심입니다.', references: [{ id: 'dm-7', title: '메타인지와 학습 효율의 관계', source_type: 'PDF', created_at: '2026-02-09' }, { id: 'dm-2', title: '스토아 철학과 현대 인지행동치료의 연결', source_type: 'WEB', created_at: '2026-02-14' }] },
  ],
}

// ─── 저널 ──────────────────────────────────────────────────────────────────

export const DEMO_JOURNAL_DATES = [
  '2026-02-18', '2026-02-17', '2026-02-15', '2026-02-13', '2026-02-10',
]

export interface DemoJournal {
  id: string
  date: string
  content: string
  mood: string
}

export const DEMO_JOURNALS: Record<string, DemoJournal> = {
  '2026-02-18': { id: 'dj-1', date: '2026-02-18', content: '오늘 트랜스포머와 멀티 에이전트 시스템의 연결고리를 발견했다. Self-Attention과 에이전트의 상태 관리가 결국 같은 문제를 다른 스케일에서 풀고 있다는 점이 흥미롭다.\n\nMmemoir을 쓰면서 이런 연결을 자연스럽게 발견하게 되는 것 같다. 기억을 체계적으로 정리하면 새로운 통찰이 생기는 경험.', mood: '🧠' },
  '2026-02-17': { id: 'dj-2', date: '2026-02-17', content: '주말에 함수형 프로그래밍 관련 메모를 다시 읽어봤다. 불변성의 원칙이 단순히 코딩 스타일이 아니라 사고의 명확성과도 연결된다는 생각.\n\n스토아 철학에서 말하는 "통제할 수 있는 것과 없는 것의 구분"이 순수 함수의 부작용 없는 설계와 비슷하다.', mood: '💡' },
  '2026-02-15': { id: 'dj-3', date: '2026-02-15', content: '오늘 아침 조깅을 하면서 BDNF와 뇌 건강에 대해 생각했다. 운동 후에 확실히 머리가 맑아지는 느낌이 드는데, 이게 과학적으로 입증된 현상이라니.\n\n운동→BDNF 증가→해마 뉴런 생성→학습 능력 향상의 선순환을 만들어가자.', mood: '🏃' },
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
