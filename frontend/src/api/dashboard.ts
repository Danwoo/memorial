import { get } from './client'
import type { StatsData, DigestData } from '../types'

// 대시보드 통계 요약 조회
export function fetchStats(): Promise<StatsData> {
  return get<StatsData>('/stats/overview')
}

// 오늘의 다이제스트 조회
export function fetchDigest(): Promise<DigestData> {
  return get<DigestData>('/digest/today')
}
