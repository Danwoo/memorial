import { get, post, postFormData } from './client'
import type { Memory, MemoryCreatePayload, PaginatedResponse } from '../types'

// 메모리 목록 조회 (페이지네이션)
export function fetchMemories(): Promise<PaginatedResponse<Memory>> {
  return get<PaginatedResponse<Memory>>('/memories')
}

// 새 메모리 생성 (웹 URL 또는 노트)
export function createMemory(payload: MemoryCreatePayload): Promise<Memory> {
  return post<Memory>('/memories', payload)
}

// PDF 파일 업로드로 메모리 생성
export function uploadPdfMemory(file: File): Promise<{ id: string; status: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return postFormData<{ id: string; status: string }>('/memories/upload-pdf', formData)
}
