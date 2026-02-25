import { useState, useEffect, useRef, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { getViewCache, setViewCache, invalidateViewCache } from '../utils/viewCache'

interface UseViewCacheOptions<T> {
  // 캐시 키 (null이면 비활성화 — 조건부 fetching 지원)
  key: string | null
  // 데이터를 가져오는 비동기 함수
  fetcher: () => Promise<T>
  // 캐시 유효 기간 (기본 60초)
  ttl?: number
}

interface UseViewCacheReturn<T> {
  data: T | null
  isLoading: boolean
  // 캐시 무효화 후 즉시 재조회
  refresh: () => Promise<void>
}

export function useViewCache<T>(options: UseViewCacheOptions<T>): UseViewCacheReturn<T> {
  const { key, fetcher, ttl } = options
  const { user } = useAuth()
  const userId = user?.id ?? ''
  const isMounted = useRef(true)

  // 마운트 시 캐시에서 초기값 로드
  const cached = key && userId ? getViewCache<T>(userId, key, ttl) : null
  const [data, setData] = useState<T | null>(cached)
  const [isLoading, setIsLoading] = useState(!cached)

  // fetcher를 ref로 관리하여 useEffect dependency 안정화
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  useEffect(() => {
    isMounted.current = true

    if (!key || !userId) {
      setIsLoading(false)
      return
    }

    // 유효한 캐시가 있으면 fetch 스킵
    if (getViewCache(userId, key, ttl)) {
      setIsLoading(false)
      return
    }

    setIsLoading(true)

    fetcherRef.current()
      .then(result => {
        if (!isMounted.current) return
        setViewCache(userId, key, result)
        setData(result)
        setIsLoading(false)
      })
      .catch(() => {
        if (!isMounted.current) return
        setIsLoading(false)
      })

    return () => { isMounted.current = false }
    // key가 바뀌면 (예: MindmapView의 viewMode 변경) 재실행
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, userId, ttl])

  const refresh = useCallback(async () => {
    if (!key || !userId) return
    invalidateViewCache(userId, key)
    setIsLoading(true)
    try {
      const result = await fetcherRef.current()
      if (!isMounted.current) return
      setViewCache(userId, key, result)
      setData(result)
    } finally {
      if (isMounted.current) setIsLoading(false)
    }
  }, [key, userId])

  return { data, isLoading, refresh }
}
