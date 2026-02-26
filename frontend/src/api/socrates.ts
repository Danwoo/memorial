import { get, post, postRaw } from './client'
import type { SocratesSessionResponse, SocratesMessage, SocratesMessagePayload, SocratesStreamChunk, SocratesReference, SocratesFeedback } from '../types'
import { isDemoMode } from '../contexts/DemoContext'
import { DEMO_SOCRATES_SESSIONS, DEMO_SOCRATES_MESSAGES, DEMO_SOCRATES_RESPONSES } from '../data/demo-data'

function createDemoSSEResponse(userMessage: string): Response {
  const match = DEMO_SOCRATES_RESPONSES.find(r =>
    r.keywords.some(k => userMessage.includes(k))
  ) ?? DEMO_SOCRATES_RESPONSES[0]

  const encoder = new TextEncoder()
  let index = 0

  const stream = new ReadableStream({
    async pull(controller) {
      if (index < match.content.length) {
        const chunk = match.content.slice(index, index + 3)
        index += 3
        const data = JSON.stringify({ content: chunk })
        controller.enqueue(encoder.encode(`data: ${data}\n\n`))
        await new Promise(r => setTimeout(r, 30))
      } else {
        const doneData = JSON.stringify({
          done: true,
          title: '데모 대화',
          references: match.references,
        })
        controller.enqueue(encoder.encode(`data: ${doneData}\n\n`))
        controller.close()
      }
    },
  })

  return new Response(stream, {
    headers: { 'Content-Type': 'text/event-stream' },
  })
}

// 새 소크라테스 세션 생성
export function createSocratesSession(): Promise<SocratesSessionResponse> {
  if (isDemoMode()) return Promise.resolve(DEMO_SOCRATES_SESSIONS[0])
  return post<SocratesSessionResponse>('/socrates/sessions', {})
}

// 사용자의 전체 소크라테스 세션 목록 조회
export function fetchSocratesSessions(): Promise<SocratesSessionResponse[]> {
  if (isDemoMode()) return Promise.resolve(DEMO_SOCRATES_SESSIONS)
  return get<SocratesSessionResponse[]>('/socrates/sessions')
}

// 특정 세션의 소크라테스 히스토리 조회
export function fetchSocratesHistory(sessionId: string): Promise<SocratesMessage[]> {
  if (isDemoMode()) return Promise.resolve(DEMO_SOCRATES_MESSAGES[sessionId] ?? [])
  return get<SocratesMessage[]>(`/socrates/sessions/${sessionId}/history`)
}

// 메시지 피드백 전송
export function sendFeedback(
  sessionId: string,
  messageIndex: number,
  rating: 'good' | 'bad',
): Promise<{ success: boolean }> {
  if (isDemoMode()) return Promise.resolve({ success: true })
  return post<{ success: boolean }>(`/socrates/sessions/${sessionId}/feedback`, {
    message_index: messageIndex,
    rating,
  })
}

// 세션의 피드백 목록 조회
export function fetchFeedbacks(sessionId: string): Promise<SocratesFeedback[]> {
  if (isDemoMode()) return Promise.resolve([])
  return get<SocratesFeedback[]>(`/socrates/sessions/${sessionId}/feedbacks`)
}

// 메시지 전송 후 SSE 스트림 응답 수신
export function sendSocratesMessage(
  sessionId: string,
  payload: SocratesMessagePayload,
  signal?: AbortSignal,
): Promise<Response> {
  if (isDemoMode()) return Promise.resolve(createDemoSSEResponse(payload.content))
  return postRaw(`/socrates/sessions/${sessionId}/messages`, payload, signal)
}

export interface SSEResult {
  content: string
  title?: string
  references?: SocratesReference[]
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
  let references: SocratesReference[] | undefined

  try {
    let finished = false
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
          const data: SocratesStreamChunk = JSON.parse(line.slice(6))
          if (data.error) {
            throw new Error(data.error)
          }
          if (data.done) {
            if (data.title) title = data.title
            finished = true
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
      if (finished) break
    }
  } finally {
    reader.releaseLock()
  }

  return { content, title, references }
}
