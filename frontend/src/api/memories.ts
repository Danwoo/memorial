import { get, post, patch, del, postFormData } from './client'
import type { Memory, MemoryDetail, MemoryCreatePayload, PaginatedResponse, LinkedJournal } from '../types'
import { isDemoMode } from '../contexts/DemoContext'
import { DEMO_MEMORIES, DEMO_MEMORY_DETAILS, DEMO_TAGS, demoPaginated } from '../data/demo-data'

export interface MemoryListParams {
  page?: number
  limit?: number
  search?: string
  tags?: string[]
  source_type?: string
  date_from?: string
  date_to?: string
  sort_by?: 'created_at' | 'updated_at' | 'title'
  sort_order?: 'asc' | 'desc'
}

// 메모리 목록 조회 (페이지네이션 + 필터 + 정렬)
export function fetchMemories(params?: MemoryListParams): Promise<PaginatedResponse<Memory>> {
  if (isDemoMode()) {
    let filtered = [...DEMO_MEMORIES]
    if (params?.search) {
      const q = params.search.toLowerCase()
      filtered = filtered.filter(m =>
        m.title.toLowerCase().includes(q) || (m.summary ?? '').toLowerCase().includes(q)
      )
    }
    if (params?.source_type) {
      filtered = filtered.filter(m => m.source_type === params.source_type)
    }
    if (params?.tags && params.tags.length > 0) {
      filtered = filtered.filter(m =>
        params.tags!.some(t => m.tags?.includes(t))
      )
    }
    if (params?.sort_by === 'title') {
      filtered.sort((a, b) => a.title.localeCompare(b.title) * (params.sort_order === 'desc' ? -1 : 1))
    } else if (params?.sort_by === 'created_at' || !params?.sort_by) {
      filtered.sort((a, b) => b.created_at.localeCompare(a.created_at) * (params?.sort_order === 'asc' ? -1 : 1))
    }
    return Promise.resolve(demoPaginated(filtered, params?.page, params?.limit))
  }
  if (!params) return get<PaginatedResponse<Memory>>('/memories')

  const sp = new URLSearchParams()
  if (params.page) sp.set('page', String(params.page))
  if (params.limit) sp.set('limit', String(params.limit))
  if (params.search) sp.set('search', params.search)
  if (params.tags && params.tags.length > 0) sp.set('tags', params.tags.join(','))
  if (params.source_type) sp.set('source_type', params.source_type)
  if (params.date_from) sp.set('date_from', params.date_from)
  if (params.date_to) sp.set('date_to', params.date_to)
  if (params.sort_by) sp.set('sort_by', params.sort_by)
  if (params.sort_order) sp.set('sort_order', params.sort_order)

  const qs = sp.toString()
  return get<PaginatedResponse<Memory>>(`/memories${qs ? `?${qs}` : ''}`)
}

// 새 메모리 생성 (웹 URL 또는 노트)
export function createMemory(payload: MemoryCreatePayload): Promise<Memory> {
  if (isDemoMode()) return Promise.reject(new Error('데모 모드에서는 메모리를 생성할 수 없습니다.'))
  return post<Memory>('/memories', payload)
}

// 단일 메모리 상세 조회
export function fetchMemoryDetail(memoryId: string): Promise<MemoryDetail> {
  if (isDemoMode()) return Promise.resolve(DEMO_MEMORY_DETAILS[memoryId] ?? DEMO_MEMORY_DETAILS['dm-1'])
  return get<MemoryDetail>(`/memories/${memoryId}`)
}

// 메모리 삭제
export function deleteMemory(memoryId: string): Promise<void> {
  if (isDemoMode()) return Promise.reject(new Error('데모 모드에서는 메모리를 삭제할 수 없습니다.'))
  return del(`/memories/${memoryId}`)
}

// 메모리 수정 (제목, 요약, 태그)
export function updateMemory(
  memoryId: string,
  body: { title?: string; summary?: string; tags?: string[] },
): Promise<MemoryDetail> {
  if (isDemoMode()) return Promise.reject(new Error('데모 모드에서는 메모리를 수정할 수 없습니다.'))
  return patch<MemoryDetail>(`/memories/${memoryId}`, body)
}

// 사용자의 기존 태그 목록 조회 (자동완성용)
export function fetchUserTags(prefix = ''): Promise<string[]> {
  if (isDemoMode()) {
    if (!prefix) return Promise.resolve(DEMO_TAGS)
    const p = prefix.toLowerCase()
    return Promise.resolve(DEMO_TAGS.filter(t => t.toLowerCase().includes(p)))
  }
  const q = prefix ? `?q=${encodeURIComponent(prefix)}` : ''
  return get<string[]>(`/memories/tags${q}`)
}

// 메모리 일괄 작업 (삭제, 태그 추가/제거)
export function bulkMemoryAction(body: {
  action: 'delete' | 'add_tags' | 'remove_tags'
  memory_ids: string[]
  tags?: string[]
}): Promise<{ affected: number }> {
  if (isDemoMode()) return Promise.reject(new Error('데모 모드에서는 일괄 작업을 수행할 수 없습니다.'))
  return post<{ affected: number }>('/memories/bulk', body)
}

// PDF 파일 업로드로 메모리 생성
export function uploadPdfMemory(file: File): Promise<{ id: string; status: string }> {
  if (isDemoMode()) return Promise.reject(new Error('데모 모드에서는 PDF를 업로드할 수 없습니다.'))
  const formData = new FormData()
  formData.append('file', file)
  return postFormData<{ id: string; status: string }>('/memories/upload-pdf', formData)
}

// 메모리를 참조한 저널 목록 역참조 조회
export function fetchMemoryJournals(memoryId: string): Promise<{ journals: LinkedJournal[] }> {
  if (isDemoMode()) return Promise.resolve({ journals: [] })
  return get<{ journals: LinkedJournal[] }>(`/memories/${memoryId}/journals`)
}
