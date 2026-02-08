import { get, post } from './client'
import type { Memory, MemoryCreatePayload, PaginatedResponse } from '../types'

/** Fetch all memories (paginated list) */
export function fetchMemories(): Promise<PaginatedResponse<Memory>> {
  return get<PaginatedResponse<Memory>>('/memories')
}

/** Create a new memory (web URL or note) */
export function createMemory(payload: MemoryCreatePayload): Promise<Memory> {
  return post<Memory>('/memories', payload)
}
