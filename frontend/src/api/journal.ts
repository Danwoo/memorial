import { get, post } from './client'
import type { RelatedMemoriesResponse, ReviewQuestionsResponse, InsightsResponse, InlineAIAction, JournalDatesResponse, JournalEntry } from '../types'
import { isDemoMode } from '../contexts/DemoContext'
import { DEMO_JOURNAL_DATES, DEMO_JOURNAL_ENTRIES, DEMO_JOURNAL_ANALYSIS, DEMO_REVIEW_QUESTIONS, DEMO_RELATED_MEMORIES } from '../data/demo-data'

export function saveJournal(content: string, memoryIds?: string[]): Promise<void> {
  if (isDemoMode()) return Promise.resolve()
  const body: { content: string; memory_ids?: string[] } = { content }
  if (memoryIds && memoryIds.length > 0) {
    body.memory_ids = memoryIds
  }
  return post('/journals', body)
}

export function fetchRelatedMemories(content: string): Promise<RelatedMemoriesResponse> {
  if (isDemoMode()) return Promise.resolve(DEMO_RELATED_MEMORIES)
  return post<RelatedMemoriesResponse>('/journals/related-memories', { content })
}

export function generateJournalDraft(sessionId: string): Promise<{ draft: string; session_id: string }> {
  if (isDemoMode()) return Promise.resolve({ draft: '오늘 하루를 돌아보며, 새로 배운 것들과 느낀 점을 정리해본다.\n\n가장 인상 깊었던 것은...', session_id: 'ds-1' })
  return post<{ draft: string; session_id: string }>('/journals/generate-draft', { session_id: sessionId })
}

export function fetchReviewQuestions(content: string): Promise<ReviewQuestionsResponse> {
  if (isDemoMode()) return Promise.resolve(DEMO_REVIEW_QUESTIONS)
  return post<ReviewQuestionsResponse>('/journals/review-questions', { content })
}

export function fetchInsights(content: string): Promise<InsightsResponse> {
  if (isDemoMode()) return Promise.resolve(DEMO_JOURNAL_ANALYSIS)
  return post<InsightsResponse>('/journals/insights', { content })
}

export async function postInlineAssist(content: string, action: InlineAIAction): Promise<{ result: string }> {
  if (isDemoMode()) return Promise.resolve({ result: '회원가입 후 AI 기능을 사용할 수 있습니다.' })
  return post<{ result: string }>('/journals/inline-assist', { content, action })
}

export function fetchJournalDates(limit = 90): Promise<JournalDatesResponse> {
  if (isDemoMode()) {
    return Promise.resolve({
      dates: DEMO_JOURNAL_DATES.map(d => ({ date: d, count: 1, mood: 'NEUTRAL' as string | null })),
    })
  }
  return get<JournalDatesResponse>(`/journals/dates?limit=${limit}`)
}

export function fetchJournalsByDate(date: string): Promise<JournalEntry[]> {
  if (isDemoMode()) {
    const entry = DEMO_JOURNAL_ENTRIES[date]
    return Promise.resolve(entry ? [entry] : [])
  }
  return get<JournalEntry[]>(`/journals/by-date/${date}`)
}
