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

/** Props for the ChatView component */
export interface ChatViewProps {
  sessionId: string | null
  onSessionCreate: (id: string) => void
}

/** Payload sent when creating a new chat message */
export interface ChatMessagePayload {
  content: string
  mode?: ChatMode
}

/** Shape of a single SSE data chunk from the streaming response */
export interface ChatStreamChunk {
  content?: string
}

/** Response from creating a new chat session */
export interface ChatSessionResponse {
  id: string
}
