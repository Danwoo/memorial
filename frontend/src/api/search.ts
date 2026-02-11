import { get } from './client'
import type { SearchResult, SearchResponse } from '../types'

interface SearchParams {
  q: string
  limit?: number
  source_type?: string
  days?: string
}

// 저장된 메모리에 대한 시맨틱 검색 수행
export function searchMemories(params: SearchParams): Promise<SearchResponse<SearchResult>> {
  const query = new URLSearchParams()
  query.set('q', params.q)
  query.set('limit', String(params.limit ?? 20))
  if (params.source_type) query.set('source_type', params.source_type)
  if (params.days) query.set('days', params.days)

  return get<SearchResponse<SearchResult>>(`/search?${query}`)
}
