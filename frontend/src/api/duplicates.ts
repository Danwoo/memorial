import { get, post } from './client'
import { isDemoMode } from '../contexts/DemoContext'

export interface DuplicatePairItem {
  id: string
  title: string
  summary: string | null
  source_type: string
  source_url: string | null
  tags: string[] | null
}

export interface DuplicatePair {
  scrap_a: DuplicatePairItem
  scrap_b: DuplicatePairItem
  similarity: number
  reason: string
}

export interface DuplicatesResponse {
  pairs: DuplicatePair[]
  total: number
}

export interface MergeResponse {
  kept_id: string
  merged_tags: string[]
}

export function fetchDuplicates(): Promise<DuplicatesResponse> {
  if (isDemoMode()) return Promise.resolve({ pairs: [], total: 0 })
  return get<DuplicatesResponse>('/scraps/duplicates')
}

export function mergeScraps(keepId: string, mergeId: string): Promise<MergeResponse> {
  if (isDemoMode()) return Promise.reject(new Error('데모 모드에서는 병합할 수 없습니다.'))
  return post<MergeResponse>('/scraps/duplicates/merge', {
    keep_id: keepId,
    merge_id: mergeId,
  })
}
