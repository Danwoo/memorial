import { post } from './client'
import type { RelatedMemoriesResponse, ReviewQuestionsResponse, InsightsResponse, InlineAIAction } from '../types'

export function saveJournal(content: string): Promise<void> {
  return post('/journals', { content })
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
