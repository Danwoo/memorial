export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatMessagePayload {
  content: string
}

export interface ChatStreamChunk {
  content?: string
  done?: boolean
  error?: string
  title?: string
}

export interface ChatSessionResponse {
  id: string
  title: string
  created_at: string
}

export interface ChatLocationState {
  newSession?: boolean
  topic?: string
}
