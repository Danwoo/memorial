import { get, post, postFormData } from './client'
import type { Memory, MemoryCreatePayload, PaginatedResponse } from '../types'

/** Fetch all memories (paginated list) */
export function fetchMemories(): Promise<PaginatedResponse<Memory>> {
  return get<PaginatedResponse<Memory>>('/memories')
}

/** Create a new memory (web URL or note) */
export function createMemory(payload: MemoryCreatePayload): Promise<Memory> {
  return post<Memory>('/memories', payload)
}

/** Upload a PDF file as a new memory */
export function uploadPdfMemory(file: File): Promise<{ id: string; status: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return postFormData<{ id: string; status: string }>('/memories/upload-pdf', formData)
}
