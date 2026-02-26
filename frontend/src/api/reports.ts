import { get } from './client'
import { isDemoMode } from '../contexts/DemoContext'
import { DEMO_WEEKLY_REPORT, DEMO_MONTHLY_REPORT } from '../data/demo-data'

export interface TopicDistribution {
  topic: string
  count: number
  percentage: number
}

export interface SourceDistribution {
  source_type: string
  count: number
  percentage: number
}

export interface ReportData {
  period: string
  date_range: string
  total_scraps: number
  total_diaries: number
  topic_distribution: TopicDistribution[]
  source_distribution: SourceDistribution[]
  llm_summary: string
  highlights: string[]
}

export function fetchWeeklyReport(): Promise<ReportData> {
  if (isDemoMode()) return Promise.resolve(DEMO_WEEKLY_REPORT)
  return get<ReportData>('/reports/weekly')
}

export function fetchMonthlyReport(): Promise<ReportData> {
  if (isDemoMode()) return Promise.resolve(DEMO_MONTHLY_REPORT)
  return get<ReportData>('/reports/monthly')
}
