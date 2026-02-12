import type { Memory } from './memory'

export interface TimelineGroup {
  date: string
  memories: Memory[]
}

export interface TimelineData {
  page: number
  limit: number
  timeline: TimelineGroup[]
  has_more: boolean
}
