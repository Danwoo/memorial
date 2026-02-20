import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Plus, X, Check, Copy } from 'lucide-react'
import { useToast } from '../contexts/ToastContext'
import { bulkMemoryAction } from '../api'
import { useMemoryList } from '../hooks/useMemoryList'
import { useMemoryTimeline } from '../hooks/useMemoryTimeline'
import { useMemorySearch } from '../hooks/useMemorySearch'
import { useBulkSelection } from '../hooks/useBulkSelection'
import MemoryAllTab from './memory/MemoryAllTab'
import MemoryTimelineTab from './memory/MemoryTimelineTab'
import MemorySearchTab from './memory/MemorySearchTab'
import AddMemoryModal from './memory/AddMemoryModal'
import BulkActionBar from './memory/BulkActionBar'
import BulkTagModal from './memory/BulkTagModal'
import MemoryDetailModal from './MemoryDetailModal'
import DuplicateModal from './DuplicateModal'
import './MemoryView.css'

type MemoryTab = 'all' | 'timeline' | 'search'

export default function MemoryView() {
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = (searchParams.get('tab') as MemoryTab) || 'all'
  const [activeTab, setActiveTab] = useState<MemoryTab>(initialTab)

  // ── 상태 훅 ──
  const memoryList = useMemoryList()
  const { loadMemories } = memoryList
  const timeline = useMemoryTimeline(activeTab === 'timeline')
  const search = useMemorySearch()
  const bulk = useBulkSelection(memoryList.memories)

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
    <div className="memory-view">
      <div className="memory-header">
        <div>
          <h1>기억</h1>
          <p className="memory-subtitle">저장된 지식을 탐색하세요</p>
        </div>
        <div className="memory-header-actions">
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
        </div>
      </div>

      <div className="memory-tabs">
        <button className={`memory-tab ${activeTab === 'all' ? 'active' : ''}`} onClick={() => handleTabChange('all')}>
          전체
        </button>
        <button className={`memory-tab ${activeTab === 'timeline' ? 'active' : ''}`} onClick={() => handleTabChange('timeline')}>
          타임라인
        </button>
        <button className={`memory-tab ${activeTab === 'search' ? 'active' : ''}`} onClick={() => handleTabChange('search')}>
          검색
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
        {activeTab === 'search' && (
          <MemorySearchTab
            query={search.query}
            onQueryChange={search.setQuery}
            results={search.results}
            isSearching={search.isSearching}
            hasSearched={search.hasSearched}
            showFilters={search.showFilters}
            onToggleFilters={() => search.setShowFilters(!search.showFilters)}
            sourceFilter={search.sourceFilter}
            onSourceFilterChange={search.setSourceFilter}
            daysFilter={search.daysFilter}
            onDaysFilterChange={search.setDaysFilter}
            hasFilters={search.hasFilters}
            onClearFilters={search.clearFilters}
            onSearch={search.handleSearch}
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
    </div>
  )
}
