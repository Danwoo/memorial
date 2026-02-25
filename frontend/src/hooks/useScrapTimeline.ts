import { useState, useRef, useEffect, useCallback } from 'react'
import type { TimelineData } from '../types'
import { fetchTimeline } from '../api'

export function useScrapTimeline(active: boolean) {
  const [data, setData] = useState<TimelineData | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const observerRef = useRef<IntersectionObserver | null>(null)
  const loadMoreRef = useRef<HTMLDivElement>(null)

  const loadTimeline = useCallback(async (pageNum: number, append = false) => {
    try {
      if (pageNum === 1) setLoading(true)
      else setLoadingMore(true)

      const newData = await fetchTimeline(pageNum)

      if (append) {
        setData(prev => {
          if (!prev) return newData
          const merged = prev.timeline.map(g => ({
            ...g,
            scraps: [...g.scraps],
          }))
          for (const group of newData.timeline) {
            const existing = merged.find(g => g.date === group.date)
            if (existing) {
              existing.scraps = [...existing.scraps, ...group.scraps]
            } else {
              merged.push(group)
            }
          }
          return { ...newData, timeline: merged }
        })
      } else {
        setData(newData)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '알 수 없는 오류')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [])

  useEffect(() => {
    if (active && !data) {
      loadTimeline(1)
    }
  }, [active, data, loadTimeline])

  // 무한 스크롤
  useEffect(() => {
    if (!active) return
    if (observerRef.current) observerRef.current.disconnect()

    observerRef.current = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && data?.has_more && !loadingMore) {
        const nextPage = page + 1
        setPage(nextPage)
        loadTimeline(nextPage, true)
      }
    })

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current)
    }

    return () => observerRef.current?.disconnect()
  }, [active, data?.has_more, loadingMore, page, loadTimeline])

  return {
    data,
    loading,
    loadingMore,
    error,
    loadMoreRef,
    loadTimeline,
  }
}
