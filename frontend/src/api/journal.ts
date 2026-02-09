import { get, post } from './client'
import type { RelatedMemoriesResponse, ChatSessionItem } from '../types'

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

/** Fetch chat sessions for the current user */
export function fetchChatSessions(): Promise<ChatSessionItem[]> {
  return get<ChatSessionItem[]>('/chat/sessions')
}
