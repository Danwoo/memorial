import { get, post, patch, del, postFormData } from './client'
import type { Memory, MemoryDetail, MemoryCreatePayload, PaginatedResponse, LinkedJournal } from '../types'

// 메모리 목록 조회 (페이지네이션)
export function fetchMemories(): Promise<PaginatedResponse<Memory>> {
  return get<PaginatedResponse<Memory>>('/memories')
}

// 새 메모리 생성 (웹 URL 또는 노트)
export function createMemory(payload: MemoryCreatePayload): Promise<Memory> {
  return post<Memory>('/memories', payload)
}

// 단일 메모리 상세 조회
export function fetchMemoryDetail(memoryId: string): Promise<MemoryDetail> {
  return get<MemoryDetail>(`/memories/${memoryId}`)
}

// 메모리 삭제
export function deleteMemory(memoryId: string): Promise<void> {
  return del(`/memories/${memoryId}`)
}

// 메모리 수정 (제목, 요약, 태그)
export function updateMemory(
  memoryId: string,
  body: { title?: string; summary?: string; tags?: string[] },
): Promise<MemoryDetail> {
  return patch<MemoryDetail>(`/memories/${memoryId}`, body)
}

// 사용자의 기존 태그 목록 조회 (자동완성용)
export function fetchUserTags(prefix = ''): Promise<string[]> {
  const q = prefix ? `?q=${encodeURIComponent(prefix)}` : ''
  return get<string[]>(`/memories/tags${q}`)
}

// 메모리 일괄 작업 (삭제, 태그 추가/제거)
export function bulkMemoryAction(body: {
  action: 'delete' | 'add_tags' | 'remove_tags'
  memory_ids: string[]
  tags?: string[]
}): Promise<{ affected: number }> {
  return post<{ affected: number }>('/memories/bulk', body)
}

// PDF 파일 업로드로 메모리 생성
export function uploadPdfMemory(file: File): Promise<{ id: string; status: string }> {
  const formData = new FormData()
  formData.append('file', file)
  return postFormData<{ id: string; status: string }>('/memories/upload-pdf', formData)
}

// 메모리를 참조한 저널 목록 역참조 조회
export function fetchMemoryJournals(memoryId: string): Promise<{ journals: LinkedJournal[] }> {
  return get<{ journals: LinkedJournal[] }>(`/memories/${memoryId}/journals`)
}
