import { get } from './client'
import type { StatsData, DigestData } from '../types'

/** Fetch dashboard overview statistics */
export function fetchStats(): Promise<StatsData> {
  return get<StatsData>('/stats/overview')
}

/** Fetch today's digest */
export function fetchDigest(): Promise<DigestData> {
  return get<DigestData>('/digest/today')
}
