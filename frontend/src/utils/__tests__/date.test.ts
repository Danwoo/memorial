import { describe, it, expect, vi, afterEach } from 'vitest'
import { formatDateKR, timeAgo, formatRelativeDate } from '../date'

describe('formatDateKR', () => {
  it('빈 값이면 빈 문자열 반환', () => {
    expect(formatDateKR()).toBe('')
    expect(formatDateKR(undefined)).toBe('')
  })

  it('유효한 날짜 문자열을 한국어 로케일로 변환', () => {
    const result = formatDateKR('2024-03-15')
    // 한국어 로케일 형식: "2024. 3. 15." 또는 환경에 따라 유사한 형태
    expect(result).toContain('2024')
    expect(result).toContain('3')
    expect(result).toContain('15')
  })

  it('ISO 날짜 문자열도 처리 가능', () => {
    const result = formatDateKR('2024-12-25T10:30:00Z')
    expect(result).toContain('2024')
    expect(result).toContain('12')
    expect(result).toContain('25')
  })
})

describe('timeAgo', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('60초 미만이면 "방금 전" 반환', () => {
    const now = new Date()
    const tenSecondsAgo = new Date(now.getTime() - 10 * 1000).toISOString()
    expect(timeAgo(tenSecondsAgo)).toBe('방금 전')
  })

  it('60분 미만이면 "N분 전" 반환', () => {
    const now = new Date()
    const fiveMinAgo = new Date(now.getTime() - 5 * 60 * 1000).toISOString()
    expect(timeAgo(fiveMinAgo)).toBe('5분 전')
  })

  it('24시간 미만이면 "N시간 전" 반환', () => {
    const now = new Date()
    const threeHoursAgo = new Date(now.getTime() - 3 * 60 * 60 * 1000).toISOString()
    expect(timeAgo(threeHoursAgo)).toBe('3시간 전')
  })

  it('7일 미만이면 "N일 전" 반환', () => {
    const now = new Date()
    const twoDaysAgo = new Date(now.getTime() - 2 * 24 * 60 * 60 * 1000).toISOString()
    expect(timeAgo(twoDaysAgo)).toBe('2일 전')
  })

  it('30일 미만이면 "N주 전" 반환', () => {
    const now = new Date()
    const fifteenDaysAgo = new Date(now.getTime() - 15 * 24 * 60 * 60 * 1000).toISOString()
    expect(timeAgo(fifteenDaysAgo)).toBe('2주 전')
  })

  it('30일 이상이면 한국어 로케일 날짜 반환', () => {
    const now = new Date()
    const sixtyDaysAgo = new Date(now.getTime() - 60 * 24 * 60 * 60 * 1000).toISOString()
    const result = timeAgo(sixtyDaysAgo)
    // formatDateKR로 위임되므로 날짜 형식 문자열이어야 함
    expect(result).not.toContain('전')
    expect(result.length).toBeGreaterThan(0)
  })
})

describe('formatRelativeDate', () => {
  it('오늘 날짜면 "오늘" 반환', () => {
    const today = new Date().toISOString()
    expect(formatRelativeDate(today)).toBe('오늘')
  })

  it('어제 날짜면 "어제" 반환', () => {
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    expect(formatRelativeDate(yesterday.toISOString())).toBe('어제')
  })

  it('이틀 이상 지난 날짜면 장형식 날짜 반환', () => {
    const oldDate = new Date()
    oldDate.setDate(oldDate.getDate() - 10)
    const result = formatRelativeDate(oldDate.toISOString())
    // "오늘"이나 "어제"가 아닌 날짜 문자열
    expect(result).not.toBe('오늘')
    expect(result).not.toBe('어제')
    expect(result.length).toBeGreaterThan(0)
  })
})
