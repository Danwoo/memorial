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
