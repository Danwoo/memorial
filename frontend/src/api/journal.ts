import { post } from './client'
import type { RelatedMemoriesResponse } from '../types'

// 저널 항목 저장
export function saveJournal(content: string): Promise<void> {
  return post('/journals', { content })
}

// 저널 내용과 관련된 메모리 검색
export function fetchRelatedMemories(content: string): Promise<RelatedMemoriesResponse> {
  return post<RelatedMemoriesResponse>('/journals/related-memories', { content })
}

// 저녁 대화 세션으로부터 저널 초안 AI 생성
export function generateJournalDraft(sessionId: string): Promise<{ draft: string; session_id: string }> {
  return post<{ draft: string; session_id: string }>('/journals/generate-draft', { session_id: sessionId })
}
