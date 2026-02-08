import { useState, useEffect, useRef, useCallback } from 'react'
import type { TimelineData } from '../types'
import './TimelineView.css'

const API_BASE = '/api/v1'

export default function TimelineView() {
  const [data, setData] = useState<TimelineData | null>(null)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [page, setPage] = useState(1)
  const observerRef = useRef<IntersectionObserver | null>(null)
  const loadMoreRef = useRef<HTMLDivElement | null>(null)

  const loadTimeline = useCallback(async (pageNum: number, append = false) => {
    try {
      if (pageNum === 1) setLoading(true)
      else setLoadingMore(true)

      const res = await fetch(`${API_BASE}/stats/timeline?page=${pageNum}&limit=20`)
      if (!res.ok) throw new Error('Failed to load timeline')
      
      const newData: TimelineData = await res.json()
      
      if (append && data) {
        // Merge timeline groups by date
        const merged = [...data.timeline]
        
        for (const group of newData.timeline) {
          const existing = merged.find(g => g.date === group.date)
          if (existing) {
            existing.memories.push(...group.memories)
          } else {
            merged.push(group)
          }
        }
        
        setData({
          ...newData,
          timeline: merged
        })
      } else {
        setData(newData)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }, [data])

  useEffect(() => {
    loadTimeline(1)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Infinite scroll observer
  useEffect(() => {
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
  }, [data?.has_more, loadingMore, page, loadTimeline])

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr)
    const today = new Date()
    const yesterday = new Date(today)
    yesterday.setDate(yesterday.getDate() - 1)

    if (date.toDateString() === today.toDateString()) {
      return '오늘'
    } else if (date.toDateString() === yesterday.toDateString()) {
      return '어제'
    } else {
      return date.toLocaleDateString('ko-KR', {
        month: 'long',
        day: 'numeric',
        weekday: 'short'
      })
    }
  }

  const getSourceIcon = (type: string) => {
    switch (type) {
      case 'WEB': return '🌐'
      case 'PDF': return '📄'
      case 'NOTE': return '📝'
      default: return '📋'
    }
  }

  if (loading) {
    return (
      <div className="timeline-view">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>타임라인 로딩 중...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="timeline-view">
        <div className="error-state">
          <div className="error-icon">⚠️</div>
          <h3>오류 발생</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => loadTimeline(1)}>
            다시 시도
          </button>
        </div>
      </div>
    )
  }

  if (!data || data.timeline.length === 0) {
    return (
      <div className="timeline-view">
        <div className="empty-state">
          <div className="empty-icon">📅</div>
          <h3>아직 메모리가 없습니다</h3>
          <p>새로운 지식을 저장해보세요!</p>
        </div>
      </div>
    )
  }

  return (
    <div className="timeline-view">
      <div className="timeline-header">
        <h1>📅 타임라인</h1>
        <p className="timeline-subtitle">시간순으로 보는 나의 지식</p>
      </div>

      <div className="timeline-container">
        <div className="timeline-line"></div>
        
        {data.timeline.map((group, groupIdx) => (
          <div key={groupIdx} className="timeline-group">
            <div className="timeline-date-marker">
              <span className="date-label">{formatDate(group.date)}</span>
            </div>
            
            <div className="timeline-items">
              {group.memories.map((memory) => (
                <div key={memory.id} className="timeline-item glass-card">
                  <div className="item-header">
                    <span className="source-icon">{getSourceIcon(memory.source_type)}</span>
                    <h3 className="item-title">{memory.title}</h3>
                  </div>
                  
                  {memory.summary && (
                    <p className="item-summary">{memory.summary}</p>
                  )}
                  
                  {memory.tags && memory.tags.length > 0 && (
                    <div className="item-tags">
                      {memory.tags.slice(0, 3).map((tag, tagIdx) => (
                        <span key={tagIdx} className="tag">#{tag}</span>
                      ))}
                      {memory.tags.length > 3 && (
                        <span className="tag-more">+{memory.tags.length - 3}</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}

        {/* Load more trigger */}
        <div ref={loadMoreRef} className="load-more-trigger">
          {loadingMore && (
            <div className="loading-more">
              <div className="loading-spinner small"></div>
              <span>더 불러오는 중...</span>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
