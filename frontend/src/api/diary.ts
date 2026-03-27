import { get, post, put } from './client'
import type { RelatedScrapsResponse, ReviewQuestionsResponse, InsightsResponse, InlineAIAction, DiaryDatesResponse, DiaryEntry } from '../types'
import { isDemoMode } from '../contexts/DemoContext'
import { DEMO_DIARY_DATES, DEMO_DIARY_ENTRIES, DEMO_DIARY_ANALYSIS, DEMO_REVIEW_QUESTIONS, DEMO_RELATED_SCRAPS } from '../data/demo-data'

export function saveDiary(content: string, scrapIds?: string[]): Promise<void> {
  if (isDemoMode()) return Promise.resolve()
  const body: { content: string; scrap_ids?: string[] } = { content }
  if (scrapIds && scrapIds.length > 0) {
    body.scrap_ids = scrapIds
  }
  return post('/diaries', body)
}

export function fetchRelatedScraps(content: string): Promise<RelatedScrapsResponse> {
  if (isDemoMode()) return Promise.resolve(DEMO_RELATED_SCRAPS)
  return post<RelatedScrapsResponse>('/diaries/related-scraps', { content })
}

export function generateDiaryDraft(sessionId: string): Promise<{ draft: string; session_id: string }> {
  if (isDemoMode()) return Promise.resolve({ draft: '오늘 하루를 돌아보며, 새로 배운 것들과 느낀 점을 정리해본다.\n\n가장 인상 깊었던 것은...', session_id: 'ds-1' })
  return post<{ draft: string; session_id: string }>('/diaries/generate-draft', { session_id: sessionId })
}

export function fetchReviewQuestions(content: string): Promise<ReviewQuestionsResponse> {
  if (isDemoMode()) return Promise.resolve(DEMO_REVIEW_QUESTIONS)
  return post<ReviewQuestionsResponse>('/diaries/review-questions', { content })
}

export function fetchInsights(content: string): Promise<InsightsResponse> {
  if (isDemoMode()) return Promise.resolve(DEMO_DIARY_ANALYSIS)
  return post<InsightsResponse>('/diaries/insights', { content })
}

export async function postInlineAssist(content: string, action: InlineAIAction): Promise<{ result: string }> {
  if (isDemoMode()) return Promise.resolve({ result: '회원가입 후 AI 기능을 사용할 수 있습니다.' })
  return post<{ result: string }>('/diaries/inline-assist', { content, action })
}

export function fetchDiaryDates(limit = 90): Promise<DiaryDatesResponse> {
  if (isDemoMode()) {
    return Promise.resolve({
      dates: DEMO_DIARY_DATES.map(d => ({ date: d, count: 1, mood: 'NEUTRAL' as string | null })),
    })
  }
  return get<DiaryDatesResponse>(`/diaries/dates?limit=${limit}`)
}

export function updateDiary(diaryId: string, content: string, scrapIds?: string[]): Promise<void> {
  if (isDemoMode()) return Promise.resolve()
  const body: { content: string; scrap_ids?: string[] } = { content }
  if (scrapIds && scrapIds.length > 0) body.scrap_ids = scrapIds
  return put(`/diaries/${diaryId}`, body)
}

export function searchDiaries(query: string, limit = 20): Promise<DiaryEntry[]> {
  if (isDemoMode()) return Promise.resolve([])
  return get<DiaryEntry[]>(`/diaries/search?q=${encodeURIComponent(query)}&limit=${limit}`)
}

export function fetchDiariesByDate(date: string): Promise<DiaryEntry[]> {
  if (isDemoMode()) {
    const entry = DEMO_DIARY_ENTRIES[date]
    return Promise.resolve(entry ? [entry] : [])
  }
  return get<DiaryEntry[]>(`/diaries/by-date/${date}`)
}
