import { post } from './client'
import type { RelatedMemoriesResponse } from '../types'

/** Save a journal entry */
export function saveJournal(content: string): Promise<void> {
  return post('/journals', { content })
}

/** Fetch memories related to the given journal content */
export function fetchRelatedMemories(content: string): Promise<RelatedMemoriesResponse> {
  return post<RelatedMemoriesResponse>('/journals/related-memories', { content })
}

/** Generate a journal draft from an evening chat session */
export function generateJournalDraft(sessionId: string): Promise<{ draft: string; session_id: string }> {
  return post<{ draft: string; session_id: string }>('/journals/generate-draft', { session_id: sessionId })
}
