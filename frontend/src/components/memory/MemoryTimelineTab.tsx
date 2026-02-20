import { AlertCircle, CalendarX2 } from 'lucide-react'
import type { TimelineData } from '../../types'
import { formatRelativeDate } from '../../utils'
import SourceIcon from '../shared/SourceIcon'
import EmptyState from '../EmptyState'

const MAX_VISIBLE_TAGS = 3

interface MemoryTimelineTabProps {
  data: TimelineData | null
  loading: boolean
  loadingMore: boolean
  error: string | null
  loadMoreRef: React.RefObject<HTMLDivElement>
  onRetry: () => void
  onSelectMemory: (id: string) => void
}

export default function MemoryTimelineTab({
  data,
  loading,
  loadingMore,
  error,
  loadMoreRef,
  onRetry,
  onSelectMemory,
}: MemoryTimelineTabProps) {
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
        title="아직 메모리가 없습니다"
        description="새로운 지식을 저장해보세요!"
      />
    )
  }

  return (
    <div className="timeline-container">
      <div className="timeline-line"></div>
      {data.timeline.map((group) => (
        <div key={group.date} className="timeline-group">
          <div className="timeline-date-marker">
            <span className="date-label">{formatRelativeDate(group.date)}</span>
          </div>
          <div className="timeline-items">
            {group.memories.map((memory) => (
              <button key={memory.id} className="timeline-item card" onClick={() => onSelectMemory(memory.id)} style={{ cursor: 'pointer', textAlign: 'left', width: '100%' }}>
                <div className="item-header">
                  <span className="source-icon"><SourceIcon type={memory.source_type} /></span>
                  <h3 className="item-title">{memory.title}</h3>
                </div>
                {memory.summary && (
                  <p className="item-summary">{memory.summary}</p>
                )}
                {memory.tags && memory.tags.length > 0 && (
                  <div className="item-tags">
                    {memory.tags.slice(0, MAX_VISIBLE_TAGS).map((tag, tagIdx) => (
                      <span key={tagIdx} className="tag">#{tag}</span>
                    ))}
                    {memory.tags.length > MAX_VISIBLE_TAGS && (
                      <span className="tag-more">+{memory.tags.length - MAX_VISIBLE_TAGS}</span>
                    )}
                  </div>
                )}
              </button>
            ))}
          </div>
        </div>
      ))}
      <div ref={loadMoreRef} className="load-more-trigger">
        {loadingMore && (
          <div className="loading-more">
            <div className="loading-spinner small"></div>
            <span>더 불러오는 중...</span>
          </div>
        )}
      </div>
    </div>
  )
}
