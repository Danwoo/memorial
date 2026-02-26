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

export interface SocratesMessagePayload {
  content: string
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
}

export interface SocratesFeedback {
  message_index: number
  rating: 'good' | 'bad'
}
