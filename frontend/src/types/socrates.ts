export type AgentType = 'socrates' | 'librarian' | 'oracle'

export type SocratesMode =
  | 'default'
  | 'insight'
  | 'counter'
  | 'summary'
  | 'evening'
  | 'assumption'
  | 'five_whys'
  | 'dialectic'
  // Librarian 전용 모드
  | 'connection'
  | 'compare'
  | 'deep_dive'

export const SOCRATES_MODE_LABELS: Record<SocratesMode, { label: string; icon: string; description: string }> = {
  default: { label: '기본', icon: '💬', description: '자유로운 대화' },
  insight: { label: '인사이트', icon: '💡', description: '깊이 있는 통찰 탐색' },
  counter: { label: '반론', icon: '⚖️', description: '다른 관점에서 검토' },
  summary: { label: '요약', icon: '📋', description: '핵심 내용 정리' },
  evening: { label: '저녁 회고', icon: '🌙', description: '하루 돌아보기' },
  assumption: { label: '전제 분석', icon: '🔍', description: '숨겨진 가정 발견' },
  five_whys: { label: '5 Whys', icon: '🎯', description: '근본 원인 탐색' },
  dialectic: { label: '양면 비교', icon: '⚡', description: '선택지 비교 평가' },
  // Librarian 전용 모드
  connection: { label: '연결 발견', icon: '🔗', description: '스크랩 간 연결 탐색' },
  compare: { label: '비교 분석', icon: '⚖️', description: '스크랩 비교' },
  deep_dive: { label: '심층 탐구', icon: '🔭', description: '주제 심층 분석' },
}

/** 에이전트별 사용 가능한 모드 필터 */
export const AGENT_MODES: Record<AgentType, SocratesMode[]> = {
  socrates: ['default', 'insight', 'counter', 'evening', 'assumption', 'five_whys', 'dialectic'],
  librarian: ['default', 'summary', 'connection', 'compare', 'deep_dive'],
  oracle: ['default', 'insight', 'counter', 'summary', 'evening', 'assumption', 'five_whys', 'dialectic'],
}

export const AGENT_CONFIG: Record<AgentType, {
  label: string
  tagline: string
  icon: string
  color: string
}> = {
  socrates: {
    label: 'Socrates',
    tagline: '감정 코치 · 소크라테스식 반문',
    icon: '🧠',
    color: 'var(--color-warning)',
  },
  librarian: {
    label: 'Librarian',
    tagline: '지식 큐레이터 · 스크랩 탐색',
    icon: '📚',
    color: 'var(--accent-primary)',
  },
  oracle: {
    label: 'Oracle',
    tagline: '범용 대화 · 지식 동반자',
    icon: '🔮',
    color: 'var(--color-text-secondary)',
  },
}

export interface SocratesReference {
  id: string
  title: string
  source_type: string
  created_at: string
}

export interface SocratesMessage {
  role: 'user' | 'assistant'
  content: string
  references?: SocratesReference[]
}

export interface SourceContext {
  type: 'diary' | 'scrap' | 'mindmap'
  title?: string
  content_preview?: string
  tags?: string[]
  graph_neighbors?: Array<{ name: string; label: string; relation_type: string }>
}

export interface SocratesMessagePayload {
  content: string
  mode?: string
  source_context?: SourceContext
  agent_type?: AgentType
}

export interface SocratesStreamChunk {
  content?: string
  done?: boolean
  error?: string
  title?: string
  references?: SocratesReference[]
  step?: string                          // 도구 이름 (status 이벤트 시)
  status?: 'started' | 'done'           // 도구 실행 상태
  args?: string                          // 도구 인자 (선택)
  detail?: string                        // 도구 결과 상세 (선택)
  agent?: string                         // 에이전트 이름 (agent_switch 이벤트 시)
}

export interface SocratesSessionResponse {
  id: string
  title: string
  created_at: string
  agent_type?: AgentType
}

export interface SocratesLocationState {
  newSession?: boolean
  topic?: string
  initialMessage?: string
  openSocrates?: boolean
  sourceContext?: SourceContext
}

export interface SocratesFeedback {
  message_index: number
  rating: 'good' | 'bad'
}
