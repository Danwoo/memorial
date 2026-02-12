import { useState, useMemo } from 'react'
import { BookOpen, Sparkles, FileText, Zap } from 'lucide-react'
import type { DigestMemory, RelatedMemory } from '../../types'
import { MemoryCard } from './MemoryCard'
import './MemorySidebar.css'

type SidebarTab = 'today' | 'related'

interface MemorySidebarProps {
  todayMemories: DigestMemory[]
  relatedMemories: RelatedMemory[]
  isLoadingRelated: boolean
  onInsertMemory: (memory: DigestMemory | RelatedMemory) => void
  onDailySummary: () => void
  onSessionDraft: () => void
  isGenerating: boolean
}

export function MemorySidebar({
  todayMemories,
  relatedMemories,
  isLoadingRelated,
  onInsertMemory,
  onDailySummary,
  onSessionDraft,
  isGenerating,
}: MemorySidebarProps) {
  const [activeTab, setActiveTab] = useState<SidebarTab>('today')

  // 다이제스트 메모리 유형별 집계
  const topicCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    todayMemories.forEach((m) => {
      const type = m.type || 'etc'
      counts[type] = (counts[type] || 0) + 1
    })
    return counts
  }, [todayMemories])

  const memories = activeTab === 'today' ? todayMemories : relatedMemories
  const isLoading = activeTab === 'related' && isLoadingRelated

  return (
    <div className="memory-sidebar">
      <div className="memory-sidebar__tabs">
        <button
          className={`sidebar-tab ${activeTab === 'today' ? 'sidebar-tab--active' : ''}`}
          onClick={() => setActiveTab('today')}
          type="button"
        >
          <BookOpen size={14} />
          오늘의 메모리
        </button>
        <button
          className={`sidebar-tab ${activeTab === 'related' ? 'sidebar-tab--active' : ''}`}
          onClick={() => setActiveTab('related')}
          type="button"
        >
          <Sparkles size={14} />
          관련
          {isLoadingRelated && <span className="sidebar-loading-dot" />}
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
          <div className="sidebar-empty">관련 메모리 검색 중...</div>
        ) : memories.length > 0 ? (
          memories.map((m) => (
            <MemoryCard key={m.id} memory={m} onInsert={onInsertMemory} />
          ))
        ) : (
          <div className="sidebar-empty">
            {activeTab === 'today'
              ? '오늘 수집된 메모리가 없습니다.'
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
