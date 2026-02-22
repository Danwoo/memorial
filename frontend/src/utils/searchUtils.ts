const CHOSUNG = ['ㄱ','ㄲ','ㄴ','ㄷ','ㄸ','ㄹ','ㅁ','ㅂ','ㅃ','ㅅ','ㅆ','ㅇ','ㅈ','ㅉ','ㅊ','ㅋ','ㅌ','ㅍ','ㅎ']
const CHOSUNG_BASE = 0xAC00
const CHOSUNG_PERIOD = 588  // 21 * 28

/** 한글 문자열에서 초성만 추출 */
export function extractChosung(str: string): string {
  return [...str].map(ch => {
    const code = ch.charCodeAt(0)
    if (code >= 0xAC00 && code <= 0xD7A3) {
      return CHOSUNG[Math.floor((code - CHOSUNG_BASE) / CHOSUNG_PERIOD)]
    }
    return ch
  }).join('')
}

/** query가 모두 초성 문자인지 확인 */
function isChosungOnly(str: string): boolean {
  return [...str].every(ch => CHOSUNG.includes(ch))
}

/** 초성 패턴 매칭 */
function matchChosung(query: string, target: string): boolean {
  if (!isChosungOnly(query)) return false
  const targetChosung = extractChosung(target)
  return targetChosung.includes(query)
}

/** Levenshtein 편집 거리 */
function levenshtein(a: string, b: string): number {
  const m = a.length, n = b.length
  if (m === 0) return n
  if (n === 0) return m

  const dp: number[][] = Array.from({ length: m + 1 }, (_, i) =>
    Array.from({ length: n + 1 }, (_, j) => (i === 0 ? j : j === 0 ? i : 0))
  )

  for (let i = 1; i <= m; i++) {
    for (let j = 1; j <= n; j++) {
      dp[i][j] = a[i-1] === b[j-1]
        ? dp[i-1][j-1]
        : 1 + Math.min(dp[i-1][j], dp[i][j-1], dp[i-1][j-1])
    }
  }
  return dp[m][n]
}

export interface SearchCandidate {
  id: string
  name: string
  label: string
  val: number
  score: number
  matchType: 'exact' | 'substring' | 'chosung' | 'fuzzy'
}

/** 노드 목록에서 스마트 검색 */
export function smartSearch(
  query: string,
  nodes: Array<{ id: string; name?: string; label: string; val?: number }>,
  maxResults = 10,
): SearchCandidate[] {
  if (!query.trim()) return []

  const q = query.trim().toLowerCase()
  const candidates: SearchCandidate[] = []

  for (const node of nodes) {
    const name = (node.name || node.id)
    const nameLower = name.toLowerCase()
    const val = node.val || 1

    // 1. 정확 매칭
    if (nameLower === q) {
      candidates.push({ id: node.id, name, label: node.label, val, score: 0, matchType: 'exact' })
      continue
    }

    // 2. 부분 문자열
    if (nameLower.includes(q)) {
      const pos = nameLower.indexOf(q)
      candidates.push({ id: node.id, name, label: node.label, val, score: 10 + pos, matchType: 'substring' })
      continue
    }

    // 3. 초성 매칭
    if (matchChosung(q, name)) {
      candidates.push({ id: node.id, name, label: node.label, val, score: 50, matchType: 'chosung' })
      continue
    }

    // 4. 퍼지 매칭 (편집 거리)
    const maxDist = q.length <= 3 ? 1 : 2
    const dist = levenshtein(q, nameLower.substring(0, q.length + maxDist))
    if (dist <= maxDist) {
      candidates.push({ id: node.id, name, label: node.label, val, score: 100 + dist * 10, matchType: 'fuzzy' })
    }
  }

  candidates.sort((a, b) => a.score - b.score || b.val - a.val)
  return candidates.slice(0, maxResults)
}
