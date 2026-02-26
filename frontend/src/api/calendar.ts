import { get } from './client'
import type { StatsData, DigestData, StreakData, ActivityResponse, BriefingData, DailyInsightsResponse } from '../types'
import { isDemoMode } from '../contexts/DemoContext'
import { DEMO_STATS, DEMO_DIGEST, DEMO_STREAK, DEMO_ACTIVITY, DEMO_BRIEFING, DEMO_INSIGHTS } from '../data/demo-data'

// 캘린더 통계 요약 조회
export function fetchStats(): Promise<StatsData> {
  if (isDemoMode()) return Promise.resolve(DEMO_STATS)
  return get<StatsData>('/calendar/overview')
}

// 오늘의 다이제스트 조회
export function fetchDigest(): Promise<DigestData> {
  if (isDemoMode()) return Promise.resolve(DEMO_DIGEST)
  return get<DigestData>('/digest/today')
}

// 스트릭 조회
export function fetchStreak(): Promise<StreakData> {
  if (isDemoMode()) return Promise.resolve(DEMO_STREAK)
  return get<StreakData>('/calendar/streak')
}

// 활동 데이터 조회
export function fetchActivity(days: number = 30): Promise<ActivityResponse> {
  if (isDemoMode()) return Promise.resolve({ days, activity: DEMO_ACTIVITY })
  return get<ActivityResponse>(`/calendar/activity?days=${days}`)
}

// 오늘의 브리핑 조회
export function fetchBriefing(): Promise<BriefingData> {
  if (isDemoMode()) return Promise.resolve(DEMO_BRIEFING)
  return get<BriefingData>('/briefing/today')
}

// 일일 AI 인사이트 조회
export function fetchDailyInsights(): Promise<DailyInsightsResponse> {
  if (isDemoMode()) return Promise.resolve({ insights: DEMO_INSIGHTS })
  return get<DailyInsightsResponse>('/insights/daily')
}

// 특정 날짜의 다이제스트 조회
export function fetchDigestByDate(date: string): Promise<DigestData> {
  if (isDemoMode()) return Promise.resolve(DEMO_DIGEST)
  return get<DigestData>(`/digest/date/${date}`)
}
