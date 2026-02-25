import type { Scrap } from './scrap'

export interface TimelineGroup {
  date: string
  scraps: Scrap[]
}

export interface TimelineData {
  page: number
  limit: number
  timeline: TimelineGroup[]
  has_more: boolean
}
