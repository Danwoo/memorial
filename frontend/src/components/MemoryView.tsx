import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, X, Check, Copy, MoreVertical, Bot } from 'lucide-react'
import { useIsMobile } from '../hooks/useMediaQuery'
import { useToast } from '../contexts/ToastContext'
import { useSocratesChat } from '../hooks/useSocratesChat'
import { bulkMemoryAction } from '../api'
import { useMemoryList } from '../hooks/useMemoryList'
import { useMemoryTimeline } from '../hooks/useMemoryTimeline'
import { useBulkSelection } from '../hooks/useBulkSelection'
import MemoryAllTab from './memory/MemoryAllTab'
import MemoryTimelineTab from './memory/MemoryTimelineTab'
import AddMemoryModal from './memory/AddMemoryModal'
import BulkActionBar from './memory/BulkActionBar'
import BulkTagModal from './memory/BulkTagModal'
import MemoryDetailModal from './MemoryDetailModal'
import DuplicateModal from './DuplicateModal'
import SocratesChatPanel from './chat/SocratesChatPanel'
import './MemoryView.css'

type MemoryTab = 'all' | 'timeline'

export default function MemoryView() {
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = (searchParams.get('tab') as MemoryTab) || 'all'
  const [activeTab, setActiveTab] = useState<MemoryTab>(initialTab)

  // ── 상태 훅 ──
  const memoryList = useMemoryList()
  const { loadMemories } = memoryList
  const timeline = useMemoryTimeline(activeTab === 'timeline')
  const bulk = useBulkSelection(memoryList.memories)

  // ── 모바일 감지 ──
  const isMobile = useIsMobile()
  const [showOverflow, setShowOverflow] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const socratesChat = useSocratesChat({ mode: 'panel', context: { type: 'memory' } })

  // ── 모달 상태 ──
  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showDuplicateModal, setShowDuplicateModal] = useState(false)
  const [showTagModal, setShowTagModal] = useState(false)
  const [tagAction, setTagAction] = useState<'add_tags' | 'remove_tags'>('add_tags')
  const [bulkLoading, setBulkLoading] = useState(false)

  useEffect(() => {
    loadMemories()
  }, [loadMemories])

  // ── 오버플로우 메뉴 외부 클릭 닫기 ──
  useEffect(() => {
    if (!showOverflow) return
    const handleClick = () => setShowOverflow(false)
    document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [showOverflow])

  const handleTabChange = (tab: MemoryTab) => {
    setActiveTab(tab)
    bulk.exitSelectMode()
    if (tab === 'all') setSearchParams({})
    else setSearchParams({ tab })
  }

  const handleBulkDelete = async () => {
    if (bulk.selectedIds.size === 0) return
    if (!window.confirm(`${bulk.selectedIds.size}개 메모리를 삭제하시겠습니까?`)) return

    setBulkLoading(true)
    try {
      const result = await bulkMemoryAction({
        action: 'delete',
        memory_ids: Array.from(bulk.selectedIds),
      })
      toast.success(`${result.affected}개 메모리가 삭제되었습니다`)
      bulk.exitSelectMode()
      loadMemories()
    } catch {
      toast.error('일괄 삭제에 실패했습니다')
    } finally {
      setBulkLoading(false)
    }
  }

  const openTagModal = (action: 'add_tags' | 'remove_tags') => {
    setTagAction(action)
    setShowTagModal(true)
  }

  return (
    <div className={`memory-view${showChat && !isMobile ? ' memory-view--with-chat' : ''}`}>
      <div className="memory-main">
      <div className="memory-header">
        <div>
          <h1>스크랩</h1>
          <p className="memory-subtitle">저장된 지식을 탐색하세요</p>
        </div>
        <div className="memory-header-actions">
          {isMobile ? (
            <>
              {!bulk.selectMode && (
                <button className="btn btn-primary btn--icon-only" onClick={() => setShowAddModal(true)} aria-label="추가">
                  <Plus size={18} />
                </button>
              )}
              {activeTab === 'all' && memoryList.memories.length > 0 && (
                <div className="memory-overflow-wrapper">
                  <button className="btn btn-secondary btn--icon-only" onClick={() => setShowOverflow(!showOverflow)} aria-label="더보기">
                    <MoreVertical size={18} />
                  </button>
                  {showOverflow && (
                    <div className="memory-overflow-menu">
                      {memoryList.memories.length >= 10 && (
                        <button onClick={() => { setShowDuplicateModal(true); setShowOverflow(false) }}>
                          <Copy size={16} /> 중복 정리
                        </button>
                      )}
                      <button onClick={() => { bulk.toggleSelectMode(); setShowOverflow(false) }}>
                        {bulk.selectMode ? <><X size={16} /> 취소</> : <><Check size={16} /> 선택</>}
                      </button>
                    </div>
                  )}
                </div>
              )}
            </>
          ) : (
            <>
              {activeTab === 'all' && memoryList.memories.length >= 10 && !bulk.selectMode && (
                <button className="btn btn-secondary" onClick={() => setShowDuplicateModal(true)}>
                  <Copy size={16} /> 중복 정리
                </button>
              )}
              {activeTab === 'all' && memoryList.memories.length > 0 && (
                <button
                  className={`btn ${bulk.selectMode ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={bulk.toggleSelectMode}
                >
                  {bulk.selectMode ? <><X size={16} /> 취소</> : <><Check size={16} /> 선택</>}
                </button>
              )}
              {!bulk.selectMode && (
                <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
                  <Plus size={16} /> 추가
                </button>
              )}
              {!bulk.selectMode && (
                <button
                  className={`btn ${showChat ? 'btn-primary' : 'btn-secondary'}`}
                  onClick={() => setShowChat(!showChat)}
                  title="Socrates 대화"
                >
                  <Bot size={16} /> Socrates
                </button>
              )}
            </>
          )}
        </div>
      </div>

      <div className="memory-tabs">
        <button className={`memory-tab ${activeTab === 'all' ? 'active' : ''}`} onClick={() => handleTabChange('all')}>
          전체
        </button>
        <button className={`memory-tab ${activeTab === 'timeline' ? 'active' : ''}`} onClick={() => handleTabChange('timeline')}>
          타임라인
        </button>
      </div>

      <div className="memory-tab-content">
        {activeTab === 'all' && (
          <MemoryAllTab
            memories={memoryList.memories}
            isLoading={memoryList.isLoading}
            sortBy={memoryList.sortBy}
            sortOrder={memoryList.sortOrder}
            sourceFilter={memoryList.sourceFilter}
            onSortChange={(sb, so) => { memoryList.setSortBy(sb); memoryList.setSortOrder(so) }}
            onSourceFilterChange={memoryList.setSourceFilter}
            selectMode={bulk.selectMode}
            selectedIds={bulk.selectedIds}
            onToggleSelect={bulk.toggleSelect}
            onToggleSelectAll={bulk.toggleSelectAll}
            onSelectMemory={setSelectedMemoryId}
            page={memoryList.page}
            totalPages={memoryList.totalPages}
            total={memoryList.total}
            searchQuery={memoryList.searchQuery}
            onSearchChange={memoryList.setSearchQuery}
            onSearchCommit={memoryList.commitSearch}
            onSearchClear={memoryList.clearSearch}
            onPageChange={memoryList.goToPage}
          />
        )}
        {activeTab === 'timeline' && (
          <MemoryTimelineTab
            data={timeline.data}
            loading={timeline.loading}
            loadingMore={timeline.loadingMore}
            error={timeline.error}
            loadMoreRef={timeline.loadMoreRef}
            onRetry={() => timeline.loadTimeline(1)}
            onSelectMemory={setSelectedMemoryId}
          />
        )}
      </div>

      {selectedMemoryId && (
        <MemoryDetailModal
          memoryId={selectedMemoryId}
          onClose={() => setSelectedMemoryId(null)}
          onDeleted={() => { setSelectedMemoryId(null); loadMemories() }}
          onUpdated={loadMemories}
        />
      )}

      {bulk.selectMode && bulk.selectedIds.size > 0 && (
        <BulkActionBar
          selectedCount={bulk.selectedIds.size}
          loading={bulkLoading}
          onDelete={handleBulkDelete}
          onAddTags={() => openTagModal('add_tags')}
          onRemoveTags={() => openTagModal('remove_tags')}
        />
      )}

      {showTagModal && (
        <BulkTagModal
          action={tagAction}
          selectedIds={bulk.selectedIds}
          onClose={() => setShowTagModal(false)}
          onDone={() => { setShowTagModal(false); bulk.exitSelectMode(); loadMemories() }}
        />
      )}

      {showDuplicateModal && (
        <DuplicateModal
          onClose={() => setShowDuplicateModal(false)}
          onMerged={loadMemories}
        />
      )}

      {showAddModal && (
        <AddMemoryModal
          onClose={() => setShowAddModal(false)}
          onAdded={loadMemories}
        />
      )}
      </div>{/* .memory-main */}

      {/* Socrates 채팅 패널 (데스크톱: 사이드 패널, 모바일: 풀스크린 오버레이) */}
      {showChat && (
        isMobile ? (
          <div className="memory-chat-overlay">
            <div className="memory-chat-overlay__header">
              <h3>Socrates</h3>
              <button
                className="memory-chat-overlay__close"
                onClick={() => setShowChat(false)}
                type="button"
                aria-label="닫기"
              >
                <X size={20} />
              </button>
            </div>
            <SocratesChatPanel
              chat={socratesChat}
              className="socrates-chat-panel--panel"
            />
          </div>
        ) : (
          <div className="memory-chat-side">
            <div className="memory-chat-side__header">
              <Bot size={16} />
              <span>Socrates</span>
              <button
                className="memory-chat-side__close"
                onClick={() => setShowChat(false)}
                type="button"
                aria-label="패널 닫기"
              >
                <X size={16} />
              </button>
            </div>
            <SocratesChatPanel
              chat={socratesChat}
              className="socrates-chat-panel--panel"
            />
          </div>
        )
      )}
    </div>
  )
}
