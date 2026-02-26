import { useState, useMemo } from 'react'
import { BookOpen, Sparkles, FileText, Zap, ChevronUp, ChevronDown, List, LayoutList } from 'lucide-react'
import type { DigestScrap, RelatedScrap } from '../../types'
import { MemoryCard } from './MemoryCard'
import './MemorySidebar.css'

type SidebarTab = 'today' | 'related'

interface MemorySidebarProps {
  todayScraps: DigestScrap[]
  relatedScraps: RelatedScrap[]
  isLoadingRelatedScraps: boolean
  onInsertScrap: (scrap: DigestScrap | RelatedScrap) => void
  onCardClick?: (scrapId: string) => void
  onDailySummary: () => void
  onSessionDraft: () => void
  isGenerating: boolean
  collapsed?: boolean
  onToggleCollapse?: () => void
}

export function MemorySidebar({
  todayScraps,
  relatedScraps,
  isLoadingRelatedScraps,
  onInsertScrap,
  onCardClick,
  onDailySummary,
  onSessionDraft,
  isGenerating,
  collapsed,
  onToggleCollapse,
}: MemorySidebarProps) {
  const [activeTab, setActiveTab] = useState<SidebarTab>('today')
  const [compact, setCompact] = useState(() => localStorage.getItem('memoir-sidebar-compact') === '1')

  // 다이제스트 메모리 유형별 집계
  const topicCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    todayScraps.forEach((m) => {
      const type = m.type || 'etc'
      counts[type] = (counts[type] || 0) + 1
    })
    return counts
  }, [todayScraps])

  const scraps = activeTab === 'today' ? todayScraps : relatedScraps
  const isLoading = activeTab === 'related' && isLoadingRelatedScraps

  const toggleCompact = () => {
    const next = !compact
    setCompact(next)
    localStorage.setItem('memoir-sidebar-compact', next ? '1' : '0')
  }

  return (
    <div className={`memory-sidebar ${collapsed ? 'memory-sidebar--collapsed' : ''} ${compact ? 'memory-sidebar--compact' : ''}`}>
      {/* 모바일 접기/펼치기 토글 */}
      {onToggleCollapse && (
        <button className="memory-sidebar__collapse-toggle" onClick={onToggleCollapse} type="button">
          <BookOpen size={16} />
          <span>스크랩 사이드바</span>
          {collapsed ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </button>
      )}
      <div className="memory-sidebar__tabs">
        <button
          className="memory-sidebar__compact-toggle"
          onClick={toggleCompact}
          title={compact ? '상세 보기' : '컴팩트 보기'}
          type="button"
        >
          {compact ? <LayoutList size={14} /> : <List size={14} />}
        </button>
        <button
          className={`sidebar-tab ${activeTab === 'today' ? 'sidebar-tab--active' : ''}`}
          onClick={() => setActiveTab('today')}
          type="button"
        >
          <BookOpen size={14} />
          오늘의 스크랩
        </button>
        <button
          className={`sidebar-tab ${activeTab === 'related' ? 'sidebar-tab--active' : ''}`}
          onClick={() => setActiveTab('related')}
          type="button"
        >
          <Sparkles size={14} />
          관련
          {isLoadingRelatedScraps && <span className="sidebar-loading-dot" />}
        </button>
      </div>

      {activeTab === 'today' && Object.keys(topicCounts).length > 0 && (
        <div className="memory-sidebar__topics">
          {Object.entries(topicCounts).map(([type, count]) => (
            <span key={type} className="topic-tag">
              {type} {count}
            </span>
          ))}
        </div>
      )}

      <div className="memory-sidebar__list">
        {isLoading ? (
          <div className="sidebar-empty">관련 스크랩 검색 중...</div>
        ) : scraps.length > 0 ? (
          scraps.map((m) => (
            <MemoryCard key={m.id} memory={m} onInsert={onInsertScrap} onCardClick={onCardClick} />
          ))
        ) : (
          <div className="sidebar-empty">
            {activeTab === 'today'
              ? '오늘 수집된 스크랩이 없습니다.'
              : '글을 작성하시면 연관된 메모가 여기에 표시됩니다.'}
          </div>
        )}
      </div>

      <div className="memory-sidebar__actions">
        <div className="sidebar-actions-label">AI 액션</div>
        <button
          className="sidebar-action-btn"
          onClick={onDailySummary}
          disabled={isGenerating}
          type="button"
        >
          <FileText size={14} />
          하루 정리
        </button>
        <button
          className="sidebar-action-btn"
          onClick={onSessionDraft}
          disabled={isGenerating}
          type="button"
        >
          <Zap size={14} />
          세션 기반 초안
        </button>
      </div>
    </div>
  )
}
