/**
 * Returns an emoji icon for the given memory source type.
 */
export function getSourceIcon(type: string): string {
  const icons: Record<string, string> = {
    WEB: '🌐',
    PDF: '📄',
    NOTE: '📝',
  }
  return icons[type] ?? '📋'
}

/**
 * Returns a CSS class name representing similarity strength.
 */
export function getSimilarityLevel(similarity: number): 'high' | 'medium' | 'low' {
  if (similarity >= 0.8) return 'high'
  if (similarity >= 0.5) return 'medium'
  return 'low'
}
