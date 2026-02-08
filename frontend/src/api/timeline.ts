import { get } from './client'
import type { TimelineData } from '../types'

/** Fetch timeline data (paginated) */
export function fetchTimeline(page: number, limit = 20): Promise<TimelineData> {
  return get<TimelineData>(`/stats/timeline?page=${page}&limit=${limit}`)
}
