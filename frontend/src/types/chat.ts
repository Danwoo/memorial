/** A single chat message */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/** Available chat conversation modes */
export type ChatMode = '' | 'insight' | 'counter' | 'summary' | 'evening'

/** Metadata for a chat mode option in the UI */
export interface ChatModeOption {
  value: ChatMode
  label: string
  icon: string
  desc: string
}

/** Payload sent when creating a new chat message */
export interface ChatMessagePayload {
  content: string
  mode?: ChatMode
}

/** Shape of a single SSE data chunk from the streaming response */
export interface ChatStreamChunk {
  content?: string
  done?: boolean
  error?: string
}

/** Response from creating/listing a chat session */
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
