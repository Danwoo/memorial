export interface ChatReference {
  id: string
  title: string
  source_type: string
  created_at: string
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  references?: ChatReference[]
}

export interface ChatMessagePayload {
  content: string
}

export interface ChatStreamChunk {
  content?: string
  done?: boolean
  error?: string
  title?: string
  references?: ChatReference[]
}

export interface ChatSessionResponse {
  id: string
  title: string
  created_at: string
}

export interface ChatLocationState {
  newSession?: boolean
  topic?: string
  initialMessage?: string
}
