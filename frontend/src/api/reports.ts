import { get } from './client'

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
  total_memories: number
  total_journals: number
  topic_distribution: TopicDistribution[]
  source_distribution: SourceDistribution[]
  llm_summary: string
  highlights: string[]
}

export function fetchWeeklyReport(): Promise<ReportData> {
  return get<ReportData>('/reports/weekly')
}

export function fetchMonthlyReport(): Promise<ReportData> {
  return get<ReportData>('/reports/monthly')
}
