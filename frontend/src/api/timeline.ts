import { get } from './client'
import type { TimelineData } from '../types'

// 타임라인 데이터 조회 (페이지네이션)
export function fetchTimeline(page: number, limit = 20): Promise<TimelineData> {
  return get<TimelineData>(`/stats/timeline?page=${page}&limit=${limit}`)
}
