import type { Memory } from './memory'

/** A group of memories sharing the same date */
export interface TimelineGroup {
  date: string
  memories: Memory[]
}

/** Paginated timeline response from the API */
export interface TimelineData {
  page: number
  limit: number
  timeline: TimelineGroup[]
  has_more: boolean
}
