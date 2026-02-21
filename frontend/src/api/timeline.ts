import { get } from './client'
import type { TimelineData } from '../types'
import { isDemoMode } from '../contexts/DemoContext'
import { DEMO_TIMELINE } from '../data/demo-data'

// 타임라인 데이터 조회 (페이지네이션)
export function fetchTimeline(page: number, limit = 20): Promise<TimelineData> {
  if (isDemoMode()) {
    const start = (page - 1) * limit
    const slice = DEMO_TIMELINE.slice(start, start + limit)
    return Promise.resolve({
      page,
      limit,
      timeline: slice,
      has_more: start + limit < DEMO_TIMELINE.length,
    })
  }
  return get<TimelineData>(`/stats/timeline?page=${page}&limit=${limit}`)
}
