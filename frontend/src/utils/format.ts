/** 유사도 수치를 CSS 클래스명(high/medium/low)으로 변환 */
export function getSimilarityLevel(similarity: number): 'high' | 'medium' | 'low' {
  if (similarity >= 0.8) return 'high'
  if (similarity >= 0.5) return 'medium'
  return 'low'
}
