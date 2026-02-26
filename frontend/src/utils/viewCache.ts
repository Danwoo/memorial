// 뷰 캐시 — 메모리 + localStorage 이중 저장 (Stale-While-Revalidate)
//
// 보안: 모든 키에 userId를 포함하여 계정 간 데이터 격리
// 생명주기:
//   - 메모리 캐시: 탭 내 페이지 전환 시 즉시 표시 (TTL 1분)
//   - localStorage: 새로고침/재방문 시 즉시 표시 (TTL 24시간)
//   - 로그아웃 시 양쪽 모두 삭제
// 무효화: invalidate()로 특정 키, clearAll()로 전체 삭제

interface CacheEntry {
  data: unknown
  timestamp: number
  userId: string
}

const store = new Map<string, CacheEntry>()
const DEFAULT_TTL = 60_000 // 인메모리 1분
const STORAGE_TTL = 24 * 60 * 60_000 // localStorage 24시간
const STORAGE_PREFIX = 'memoir:cache:'

// userId를 포함한 내부 키 생성
function makeKey(userId: string, key: string): string {
  return `${userId}:${key}`
}

// localStorage에서 읽기
function readStorage<T>(fullKey: string, userId: string): T | null {
  try {
    const raw = localStorage.getItem(`${STORAGE_PREFIX}${fullKey}`)
    if (!raw) return null
    const entry: CacheEntry = JSON.parse(raw)
    if (entry.userId !== userId) return null
    if (Date.now() - entry.timestamp > STORAGE_TTL) {
      localStorage.removeItem(`${STORAGE_PREFIX}${fullKey}`)
      return null
    }
    return entry.data as T
  } catch {
    return null
  }
}

// localStorage에 쓰기
function writeStorage(fullKey: string, entry: CacheEntry): void {
  try {
    localStorage.setItem(`${STORAGE_PREFIX}${fullKey}`, JSON.stringify(entry))
  } catch {
    // 용량 초과 시 무시 — 인메모리 캐시로 동작
  }
}

export function getViewCache<T>(userId: string, key: string, ttl = DEFAULT_TTL): T | null {
  const fullKey = makeKey(userId, key)

  // 1순위: 인메모리 캐시 (빠름, TTL 짧음)
  const memEntry = store.get(fullKey)
  if (memEntry && memEntry.userId === userId && Date.now() - memEntry.timestamp <= ttl) {
    return memEntry.data as T
  }
  if (memEntry) store.delete(fullKey)

  // 2순위: localStorage (느리지만 영속, TTL 김)
  const stored = readStorage<T>(fullKey, userId)
  if (stored !== null) {
    // localStorage 히트 → 인메모리에도 올려서 다음 조회 가속
    const entry: CacheEntry = { data: stored, timestamp: Date.now(), userId }
    store.set(fullKey, entry)
    return stored
  }

  return null
}

export function setViewCache<T>(userId: string, key: string, data: T): void {
  const fullKey = makeKey(userId, key)
  const entry: CacheEntry = { data, timestamp: Date.now(), userId }
  store.set(fullKey, entry)
  writeStorage(fullKey, entry)
}

export function invalidateViewCache(userId: string, key: string): void {
  const fullKey = makeKey(userId, key)
  store.delete(fullKey)
  try { localStorage.removeItem(`${STORAGE_PREFIX}${fullKey}`) } catch { /* */ }
}

// 특정 프리픽스로 시작하는 캐시 일괄 삭제 (예: 'graph:' → 그래프 관련 전체)
export function invalidateByPrefix(userId: string, prefix: string): void {
  const fullPrefix = makeKey(userId, prefix)
  for (const k of store.keys()) {
    if (k.startsWith(fullPrefix)) store.delete(k)
  }
  try {
    const storagePrefix = `${STORAGE_PREFIX}${fullPrefix}`
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const lsKey = localStorage.key(i)
      if (lsKey?.startsWith(storagePrefix)) localStorage.removeItem(lsKey)
    }
  } catch { /* */ }
}

// 로그아웃 시 전체 캐시 초기화 — 반드시 동기 호출
export function clearAllViewCache(): void {
  store.clear()
  try {
    for (let i = localStorage.length - 1; i >= 0; i--) {
      const key = localStorage.key(i)
      if (key?.startsWith(STORAGE_PREFIX)) localStorage.removeItem(key)
    }
  } catch { /* */ }
}

// 캐시 키 상수 — 중앙 관리로 오타 방지 및 무효화 지점 추적
export const CACHE_KEYS = {
  DASHBOARD: 'dashboard_v2',
  SCRAP_LIST: 'scrap-list',
  GRAPH_PREFIX: 'mindmap:',
} as const
