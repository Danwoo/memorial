/**
 * Formats a date string to Korean locale short date (e.g. "2024. 2. 7.").
 * Returns empty string if input is falsy.
 */
export function formatDateKR(dateStr?: string): string {
  if (!dateStr) return ''
  return new Date(dateStr).toLocaleDateString('ko-KR')
}

/**
 * Formats a date string with relative labels for today/yesterday,
 * falling back to a Korean locale long format.
 */
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
