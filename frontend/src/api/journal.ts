import { get, post } from './client'
import type { RelatedMemoriesResponse, ReviewQuestionsResponse, InsightsResponse, InlineAIAction, JournalDatesResponse, JournalEntry } from '../types'

export function saveJournal(content: string, memoryIds?: string[]): Promise<void> {
  const body: { content: string; memory_ids?: string[] } = { content }
  if (memoryIds && memoryIds.length > 0) {
    body.memory_ids = memoryIds
  }
  return post('/journals', body)
}

export function fetchRelatedMemories(content: string): Promise<RelatedMemoriesResponse> {
  return post<RelatedMemoriesResponse>('/journals/related-memories', { content })
}

export function generateJournalDraft(sessionId: string): Promise<{ draft: string; session_id: string }> {
  return post<{ draft: string; session_id: string }>('/journals/generate-draft', { session_id: sessionId })
}

export function fetchReviewQuestions(content: string): Promise<ReviewQuestionsResponse> {
  return post<ReviewQuestionsResponse>('/journals/review-questions', { content })
}

export function fetchInsights(content: string): Promise<InsightsResponse> {
  return post<InsightsResponse>('/journals/insights', { content })
}

export async function postInlineAssist(content: string, action: InlineAIAction): Promise<{ result: string }> {
  return post<{ result: string }>('/journals/inline-assist', { content, action })
}

export function fetchJournalDates(limit = 90): Promise<JournalDatesResponse> {
  return get<JournalDatesResponse>(`/journals/dates?limit=${limit}`)
}

export function fetchJournalsByDate(date: string): Promise<JournalEntry[]> {
  return get<JournalEntry[]>(`/journals/by-date/${date}`)
}
