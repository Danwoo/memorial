export type SocratesMode =
  | 'default'
  | 'insight'
  | 'counter'
  | 'summary'
  | 'evening'
  | 'assumption'
  | 'five_whys'
  | 'dialectic'

export const SOCRATES_MODE_LABELS: Record<SocratesMode, { label: string; icon: string; description: string }> = {
  default: { label: '기본', icon: '💬', description: '자유로운 대화' },
  insight: { label: '인사이트', icon: '💡', description: '깊이 있는 통찰 탐색' },
  counter: { label: '반론', icon: '⚖️', description: '다른 관점에서 검토' },
  summary: { label: '요약', icon: '📋', description: '핵심 내용 정리' },
  evening: { label: '저녁 회고', icon: '🌙', description: '하루 돌아보기' },
  assumption: { label: '전제 분석', icon: '🔍', description: '숨겨진 가정 발견' },
  five_whys: { label: '5 Whys', icon: '🎯', description: '근본 원인 탐색' },
  dialectic: { label: '양면 비교', icon: '⚡', description: '선택지 비교 평가' },
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
}

export interface SocratesStreamChunk {
  content?: string
  done?: boolean
  error?: string
  title?: string
  references?: SocratesReference[]
}

export interface SocratesSessionResponse {
  id: string
  title: string
  created_at: string
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
