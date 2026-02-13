export interface JournalSavePayload {
  content: string
}

export interface RelatedMemoriesPayload {
  content: string
}

export type EditorMode = 'wysiwyg' | 'markdown' | 'viewer'
export type InlineAIAction = 'expand' | 'summarize' | 'refine'

export interface ReviewQuestionsResponse {
  questions: string[]
}

export interface CognitiveDistortion {
  type: string
  name: string
  trigger: string
  feedback: string
}

export interface InsightsResponse {
  has_distortions: boolean
  distortions: CognitiveDistortion[]
  wellness_score: number
}

export interface JournalDateInfo {
  date: string
  count: number
  mood: string | null
}

export interface JournalDatesResponse {
  dates: JournalDateInfo[]
}

export interface JournalEntry {
  id: string
  content: string
  mood: string | null
  created_at: string
  updated_at: string
}
