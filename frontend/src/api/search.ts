import { get } from './client'
import type { SearchResult, SearchResponse, RelatedMemory } from '../types'
import { isDemoMode } from '../contexts/DemoContext'
import { DEMO_MEMORIES } from '../data/demo-data'

interface SearchParams {
  q: string
  limit?: number
  source_type?: string
  days?: string
}

// 저장된 메모리에 대한 시맨틱 검색 수행
export function searchMemories(params: SearchParams): Promise<SearchResponse<SearchResult>> {
  if (isDemoMode()) {
    const q = params.q.toLowerCase()
    const results: SearchResult[] = DEMO_MEMORIES
      .filter(m => m.title.toLowerCase().includes(q) || (m.summary ?? '').toLowerCase().includes(q))
      .map(m => ({
        id: m.id,
        title: m.title,
        content: m.summary ?? '',
        summary: m.summary,
        source_type: m.source_type,
        similarity: 0.85,
        created_at: m.created_at,
        tags: m.tags,
      }))
    return Promise.resolve({
      query: params.q,
      results,
      total: results.length,
      filters_applied: {},
    })
  }
  const query = new URLSearchParams()
  query.set('q', params.q)
  query.set('limit', String(params.limit ?? 20))
  if (params.source_type) query.set('source_type', params.source_type)
  if (params.days) query.set('days', params.days)

  return get<SearchResponse<SearchResult>>(`/search?${query}`)
}

// 특정 메모리와 관련된 메모리 목록 조회
export function fetchRelatedMemoriesById(memoryId: string, limit = 5): Promise<RelatedMemory[]> {
  if (isDemoMode()) {
    const related: RelatedMemory[] = DEMO_MEMORIES
      .filter(m => m.id !== memoryId)
      .slice(0, limit)
      .map(m => ({
        id: m.id,
        title: m.title,
        summary: m.summary ?? '',
        type: 'semantic',
        created_at: m.created_at,
        similarity: 0.75 + Math.random() * 0.2,
      }))
    return Promise.resolve(related)
  }
  return get<RelatedMemory[]>(`/search/related/${memoryId}?limit=${limit}`)
}
