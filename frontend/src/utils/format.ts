/**
 * 소스 타입에 해당하는 Lucide 아이콘 이름 반환
 */
export function getSourceIcon(type: string): string {
  const icons: Record<string, string> = {
    WEB: 'Globe',
    PDF: 'FileText',
    NOTE: 'StickyNote',
  }
  return icons[type] ?? 'File'
}

/**
 * Returns a CSS class name representing similarity strength.
 */
export function getSimilarityLevel(similarity: number): 'high' | 'medium' | 'low' {
  if (similarity >= 0.8) return 'high'
  if (similarity >= 0.5) return 'medium'
  return 'low'
}
