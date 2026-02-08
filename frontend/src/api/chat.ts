import { post, postRaw } from './client'
import type { ChatSessionResponse, ChatMessagePayload, ChatStreamChunk } from '../types'

/** Create a new chat session */
export function createChatSession(): Promise<ChatSessionResponse> {
  return post<ChatSessionResponse>('/chat/sessions', {})
}

/** Send a message and receive an SSE stream response */
export function sendChatMessage(
  sessionId: string,
  payload: ChatMessagePayload,
  signal?: AbortSignal,
): Promise<Response> {
  return postRaw(`/chat/sessions/${sessionId}/messages`, payload, signal)
}

/**
 * Reads an SSE stream from a Response body and invokes `onChunk`
 * for each parsed data event. Returns the full accumulated content.
 */
export async function readSSEStream(
  response: Response,
  onChunk: (accumulated: string) => void,
): Promise<string> {
  const reader = response.body?.getReader()
  if (!reader) return ''

  const decoder = new TextDecoder('utf-8')
  let content = ''
  let buffer = ''

  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')

      // Keep potentially incomplete last line in the buffer
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue

        try {
          const data: ChatStreamChunk = JSON.parse(line.slice(6))
          if (data.error) {
            throw new Error(data.error)
          }
          if (data.done) break
          if (data.content) {
            content += data.content
            onChunk(content)
          }
        } catch (e) {
          if (e instanceof Error && e.message !== '') throw e
          // Ignore unparseable SSE lines
        }
      }
    }
  } finally {
    reader.releaseLock()
  }

  return content
}
