import { get } from './client'
import type { StatsData, DigestData, StreakData, ActivityResponse, BriefingData, DailyInsightsResponse } from '../types'

// 대시보드 통계 요약 조회
export function fetchStats(): Promise<StatsData> {
  return get<StatsData>('/stats/overview')
}

// 오늘의 다이제스트 조회
export function fetchDigest(): Promise<DigestData> {
  return get<DigestData>('/digest/today')
}

// 스트릭 조회
export function fetchStreak(): Promise<StreakData> {
  return get<StreakData>('/stats/streak')
}

// 활동 데이터 조회
export function fetchActivity(days: number = 30): Promise<ActivityResponse> {
  return get<ActivityResponse>(`/stats/activity?days=${days}`)
}

// 오늘의 브리핑 조회
export function fetchBriefing(): Promise<BriefingData> {
  return get<BriefingData>('/briefing/today')
}

// 일일 AI 인사이트 조회
export function fetchDailyInsights(): Promise<DailyInsightsResponse> {
  return get<DailyInsightsResponse>('/insights/daily')
}
