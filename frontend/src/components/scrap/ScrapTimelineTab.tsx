import { useState, useMemo, useEffect } from 'react'
import { AlertCircle, CalendarX2, ChevronRight, Search, X } from 'lucide-react'
import type { TimelineData } from '../../types'
import { formatRelativeDate } from '../../utils'
import SourceIcon from '../shared/SourceIcon'
import EmptyState from '../EmptyState'

const MAX_VISIBLE_TAGS = 3
const DEFAULT_EXPANDED_COUNT = 3

interface ScrapTimelineTabProps {
  data: TimelineData | null
  loading: boolean
  loadingMore: boolean
  error: string | null
  loadMoreRef: React.RefObject<HTMLDivElement>
  onRetry: () => void
  onSelectScrap: (id: string) => void
}

export default function ScrapTimelineTab({
  data,
  loading,
  loadingMore,
  error,
  loadMoreRef,
  onRetry,
  onSelectScrap,
}: ScrapTimelineTabProps) {
  const [collapsedDates, setCollapsedDates] = useState<Set<string>>(() => {
    // 초기값: 모든 날짜 접힘 (최근 3일은 나중에 제외)
    if (!data) return new Set<string>()
    return new Set(data.timeline.slice(DEFAULT_EXPANDED_COUNT).map(g => g.date))
  })

  const [searchQuery, setSearchQuery] = useState('')

  const timelineGroups = useMemo(() => data?.timeline ?? [], [data?.timeline])

  // 날짜 그룹이 추가될 때 기본 접힘 처리
  useEffect(() => {
    if (timelineGroups.length === 0) return
    setCollapsedDates(prev => {
      const next = new Set(prev)
      timelineGroups.forEach((g, i) => {
        if (i >= DEFAULT_EXPANDED_COUNT && !next.has(g.date) && prev.size > 0) {
          next.add(g.date)
        }
      })
      // 최초 로드 시
      if (prev.size === 0 && timelineGroups.length > DEFAULT_EXPANDED_COUNT) {
        timelineGroups.slice(DEFAULT_EXPANDED_COUNT).forEach(g => next.add(g.date))
      }
      return next
    })
  }, [timelineGroups])

  const toggleDate = (date: string) => {
    setCollapsedDates(prev => {
      const next = new Set(prev)
      if (next.has(date)) next.delete(date)
      else next.add(date)
      return next
    })
  }

  // 클라이언트 사이드 필터
  const filteredGroups = useMemo(() => {
    if (!searchQuery.trim()) return timelineGroups
    const q = searchQuery.toLowerCase()
    return timelineGroups
      .map(group => ({
        ...group,
        memories: group.scraps.filter(m =>
          m.title.toLowerCase().includes(q) ||
          (m.tags ?? []).some(t => t.toLowerCase().includes(q)),
        ),
      }))
      .filter(group => group.scraps.length > 0)
  }, [timelineGroups, searchQuery])

  if (loading) {
    return (
      <div className="loading-state">
        <div className="loading-spinner"></div>
        <p>타임라인 로딩 중...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="error-state">
        <AlertCircle size={48} className="state-icon" />
        <h3>오류 발생</h3>
        <p>{error}</p>
        <button className="btn btn-primary" onClick={onRetry}>
          다시 시도
        </button>
      </div>
    )
  }

  if (!data || data.timeline.length === 0) {
    return (
      <EmptyState
        icon={<CalendarX2 size={48} />}
        title="아직 스크랩이 없습니다"
        description="새로운 지식을 저장해보세요!"
      />
    )
  }

  return (
    <>
      {/* 검색바 */}
      <div className="timeline-search-bar">
        <Search size={16} className="scrap-search-bar__icon" />
        <input
          type="text"
          className="scrap-search-bar__input"
          placeholder="타임라인 내 검색..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
        />
        {searchQuery && (
          <button className="scrap-search-bar__clear" onClick={() => setSearchQuery('')} aria-label="검색 초기화">
            <X size={16} />
          </button>
        )}
      </div>

      <div className="timeline-container">
        <div className="timeline-line"></div>
        {filteredGroups.length === 0 ? (
          <EmptyState
            icon={<Search size={48} />}
            title="검색 결과가 없습니다"
            description="다른 키워드로 검색해보세요"
          />
        ) : (
          filteredGroups.map((group) => {
            const isCollapsed = collapsedDates.has(group.date)
            return (
              <div key={group.date} className="timeline-group">
                <button
                  className="timeline-date-marker"
                  onClick={() => toggleDate(group.date)}
                  type="button"
                  aria-expanded={!isCollapsed}
                >
                  <ChevronRight
                    size={16}
                    className={`timeline-date-marker__chevron ${!isCollapsed ? 'timeline-date-marker__chevron--open' : ''}`}
                  />
                  <span className="date-label">
                    {formatRelativeDate(group.date)}
                    <span className="date-label__count">({group.scraps.length})</span>
                  </span>
                </button>
                {!isCollapsed && (
                  <div className="timeline-items">
                    {group.scraps.map((scrap) => (
                      <button key={scrap.id} className="timeline-item card" onClick={() => onSelectScrap(scrap.id)} style={{ cursor: 'pointer', textAlign: 'left', width: '100%' }}>
                        <div className="item-header">
                          <span className="source-icon"><SourceIcon type={scrap.source_type} /></span>
                          <h3 className="item-title">{scrap.title}</h3>
                        </div>
                        {scrap.summary && (
                          <p className="item-summary">{scrap.summary}</p>
                        )}
                        {scrap.tags && scrap.tags.length > 0 && (
                          <div className="item-tags">
                            {scrap.tags.slice(0, MAX_VISIBLE_TAGS).map((tag, tagIdx) => (
                              <span key={tagIdx} className="tag">#{tag}</span>
                            ))}
                            {scrap.tags.length > MAX_VISIBLE_TAGS && (
                              <span className="tag-more">+{scrap.tags.length - MAX_VISIBLE_TAGS}</span>
                            )}
                          </div>
                        )}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )
          })
        )}
        <div ref={loadMoreRef} className="load-more-trigger">
          {loadingMore && (
            <div className="loading-more">
              <div className="loading-spinner small"></div>
              <span>더 불러오는 중...</span>
            </div>
          )}
        </div>
      </div>
    </>
  )
}
