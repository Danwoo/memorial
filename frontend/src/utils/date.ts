/** 날짜 문자열을 한국어 로케일 단축 날짜로 포맷 (예: "2024. 2. 7.") */
export function formatDateKR(dateStr?: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('ko-KR')
}

/** 오늘/어제는 상대 표현, 그 외는 한국어 로케일 장형식 반환 */
export function formatRelativeDate(dateStr: string): string {
  const date = new Date(dateStr)
  const today = new Date()
  const yesterday = new Date(today)
  yesterday.setDate(yesterday.getDate() - 1)

  if (date.toDateString() === today.toDateString()) {
    return '오늘'
  }
  if (date.toDateString() === yesterday.toDateString()) {
    return '어제'
  }
  return date.toLocaleDateString('ko-KR', {
    month: 'long',
    day: 'numeric',
    weekday: 'short',
  })
}
