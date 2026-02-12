export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export type ChatMode = '' | 'insight' | 'counter' | 'summary' | 'evening'

export interface ChatModeOption {
  value: ChatMode
  label: string
  icon: string
  desc: string
}

export interface ChatMessagePayload {
  content: string
  mode?: ChatMode
}

export interface ChatStreamChunk {
  content?: string
  done?: boolean
  error?: string
}

export interface ChatSessionResponse {
  id: string
  title: string
  created_at: string
}

export interface ChatLocationState {
  newSession?: boolean
  topic?: string
  mode?: string
}
