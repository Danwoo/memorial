import { get, post, postRaw } from './client'
import type { ChatSessionResponse, ChatMessage, ChatMessagePayload, ChatStreamChunk, ChatReference, ChatFeedback } from '../types'

// 새 채팅 세션 생성
export function createChatSession(): Promise<ChatSessionResponse> {
  return post<ChatSessionResponse>('/chat/sessions', {})
}

// 사용자의 전체 채팅 세션 목록 조회
export function fetchChatSessions(): Promise<ChatSessionResponse[]> {
  return get<ChatSessionResponse[]>('/chat/sessions')
}

// 특정 세션의 채팅 히스토리 조회
export function fetchChatHistory(sessionId: string): Promise<ChatMessage[]> {
  return get<ChatMessage[]>(`/chat/sessions/${sessionId}/history`)
}

// 메시지 피드백 전송
export function sendFeedback(
  sessionId: string,
  messageIndex: number,
  rating: 'good' | 'bad',
): Promise<{ success: boolean }> {
  return post<{ success: boolean }>(`/chat/sessions/${sessionId}/feedback`, {
    message_index: messageIndex,
    rating,
  })
}

// 세션의 피드백 목록 조회
export function fetchFeedbacks(sessionId: string): Promise<ChatFeedback[]> {
  return get<ChatFeedback[]>(`/chat/sessions/${sessionId}/feedbacks`)
}

// 메시지 전송 후 SSE 스트림 응답 수신
export function sendChatMessage(
  sessionId: string,
  payload: ChatMessagePayload,
  signal?: AbortSignal,
): Promise<Response> {
  return postRaw(`/chat/sessions/${sessionId}/messages`, payload, signal)
}

export interface SSEResult {
  content: string
  title?: string
  references?: ChatReference[]
}

// SSE 스트림을 읽어 청크 단위로 콜백 호출, 결과(누적 텍스트 + 자동 생성 제목) 반환
export async function readSSEStream(
  response: Response,
  onChunk: (accumulated: string) => void,
): Promise<SSEResult> {
  const reader = response.body?.getReader()
  if (!reader) return { content: '' }

  const decoder = new TextDecoder('utf-8')
  let content = ''
  let buffer = ''
  let title: string | undefined
  let references: ChatReference[] | undefined

  try {
    // eslint-disable-next-line no-constant-condition
    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')

      // 불완전한 마지막 줄은 버퍼에 보관
      buffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue

        try {
          const data: ChatStreamChunk = JSON.parse(line.slice(6))
          if (data.error) {
            throw new Error(data.error)
          }
          if (data.done) {
            if (data.title) title = data.title
            break
          }
          if (data.references) {
            references = data.references
          }
          if (data.content) {
            content += data.content
            onChunk(content)
          }
        } catch (e) {
          if (e instanceof Error && e.message !== '') throw e
          // 파싱 불가능한 SSE 라인 무시
        }
      }
    }
  } finally {
    reader.releaseLock()
  }

  return { content, title, references }
}
