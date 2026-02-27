import { useState, useEffect } from 'react'
import { useResizePanel } from '../hooks/useResizePanel'
import { useSearchParams } from 'react-router-dom'
import { Plus, X, Check, Copy, MoreVertical, Bot } from 'lucide-react'
import { useIsMobile } from '../hooks/useMediaQuery'
import { useToast } from '../contexts/ToastContext'
import { useSocratesChat } from '../hooks/useSocratesChat'
import { bulkScrapAction } from '../api'
import { useScrapList } from '../hooks/useScrapList'
import { useScrapTimeline } from '../hooks/useScrapTimeline'
import { useBulkSelection } from '../hooks/useBulkSelection'
import ScrapAllTab from './scrap/ScrapAllTab'
import ScrapTimelineTab from './scrap/ScrapTimelineTab'
import AddScrapModal from './scrap/AddScrapModal'
import BulkActionBar from './scrap/BulkActionBar'
import BulkTagModal from './scrap/BulkTagModal'
import ScrapDetailModal from './ScrapDetailModal'
import DuplicateModal from './DuplicateModal'
import SocratesPanel from './socrates/SocratesPanel'
import './ScrapView.css'

type ScrapTab = 'all' | 'timeline'

export default function ScrapView() {
  const toast = useToast()
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = (searchParams.get('tab') as ScrapTab) || 'all'
  const [activeTab, setActiveTab] = useState<ScrapTab>(initialTab)

  // ── 상태 훅 ──
  const scrapList = useScrapList()
  const { loadScraps } = scrapList
  const timeline = useScrapTimeline(activeTab === 'timeline')
  const bulk = useBulkSelection(scrapList.scraps)

  // ── 모바일 감지 ──
  const isMobile = useIsMobile()
  const { vw: socratesVw, onMouseDown: onSocratesResize } = useResizePanel(22, 15, 40, 'left', 'scrap-socrates-vw')
  const [showOverflow, setShowOverflow] = useState(false)
  const [showChat, setShowChat] = useState(false)
  const socratesChat = useSocratesChat({ mode: 'panel', context: { type: 'scrap' } })

  // ── 모달 상태 ──
  const [selectedScrapId, setSelectedScrapId] = useState<string | null>(null)
  const [showAddModal, setShowAddModal] = useState(false)
  const [showDuplicateModal, setShowDuplicateModal] = useState(false)
  const [showTagModal, setShowTagModal] = useState(false)
  const [tagAction, setTagAction] = useState<'add_tags' | 'remove_tags'>('add_tags')
  const [bulkLoading, setBulkLoading] = useState(false)

  useEffect(() => {
    loadScraps()
  }, [loadScraps])

  // ── 오버플로우 메뉴 외부 클릭 닫기 ──
  useEffect(() => {
    if (!showOverflow) return
    const handleClick = () => setShowOverflow(false)
    document.addEventListener('click', handleClick)
    return () => document.removeEventListener('click', handleClick)
  }, [showOverflow])

  const handleTabChange = (tab: ScrapTab) => {
    setActiveTab(tab)
    bulk.exitSelectMode()
    if (tab === 'all') setSearchParams({})
    else setSearchParams({ tab })
  }

  const handleBulkDelete = async () => {
    if (bulk.selectedIds.size === 0) return
    if (!window.confirm(`${bulk.selectedIds.size}개 스크랩을 삭제하시겠습니까?`)) return

    setBulkLoading(true)
    try {
      const result = await bulkScrapAction({
        action: 'delete',
        scrap_ids: Array.from(bulk.selectedIds),
      })
      toast.success(`${result.affected}개 스크랩이 삭제되었습니다`)
      bulk.exitSelectMode()
      loadScraps()
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
    <div className={`scrap-view${showChat && !isMobile ? ' scrap-view--with-socrates' : ''}`}>
      <div className="scrap-main">
      <div className="scrap-header">
        <div>
          <h1>스크랩</h1>
          <p className="scrap-subtitle">저장된 지식을 탐색하세요</p>
        </div>
        <div className="scrap-header-actions">
          {isMobile ? (
            <>
              {!bulk.selectMode && (
                <button className="btn btn-primary btn--icon-only" onClick={() => setShowAddModal(true)} aria-label="추가">
                  <Plus size={18} />
                </button>
              )}
              {activeTab === 'all' && scrapList.scraps.length > 0 && (
                <div className="scrap-overflow-wrapper">
                  <button className="btn btn-secondary btn--icon-only" onClick={() => setShowOverflow(!showOverflow)} aria-label="더보기">
                    <MoreVertical size={18} />
                  </button>
                  {showOverflow && (
                    <div className="scrap-overflow-menu">
                      {scrapList.scraps.length >= 10 && (
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
              {activeTab === 'all' && scrapList.scraps.length >= 10 && !bulk.selectMode && (
                <button className="btn btn-secondary" onClick={() => setShowDuplicateModal(true)}>
                  <Copy size={16} /> 중복 정리
                </button>
              )}
              {activeTab === 'all' && scrapList.scraps.length > 0 && (
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

      <div className="scrap-tabs">
        <button className={`scrap-tab ${activeTab === 'all' ? 'active' : ''}`} onClick={() => handleTabChange('all')}>
          전체
        </button>
        <button className={`scrap-tab ${activeTab === 'timeline' ? 'active' : ''}`} onClick={() => handleTabChange('timeline')}>
          타임라인
        </button>
      </div>

      <div className="scrap-tab-content">
        {activeTab === 'all' && (
          <ScrapAllTab
            scraps={scrapList.scraps}
            isLoading={scrapList.isLoading}
            sortBy={scrapList.sortBy}
            sortOrder={scrapList.sortOrder}
            sourceFilter={scrapList.sourceFilter}
            onSortChange={(sb, so) => { scrapList.setSortBy(sb); scrapList.setSortOrder(so) }}
            onSourceFilterChange={scrapList.setSourceFilter}
            selectMode={bulk.selectMode}
            selectedIds={bulk.selectedIds}
            onToggleSelect={bulk.toggleSelect}
            onToggleSelectAll={bulk.toggleSelectAll}
            onSelectScrap={setSelectedScrapId}
            page={scrapList.page}
            totalPages={scrapList.totalPages}
            total={scrapList.total}
            searchQuery={scrapList.searchQuery}
            onSearchChange={scrapList.setSearchQuery}
            onSearchCommit={scrapList.commitSearch}
            onSearchClear={scrapList.clearSearch}
            onPageChange={scrapList.goToPage}
          />
        )}
        {activeTab === 'timeline' && (
          <ScrapTimelineTab
            data={timeline.data}
            loading={timeline.loading}
            loadingMore={timeline.loadingMore}
            error={timeline.error}
            loadMoreRef={timeline.loadMoreRef}
            onRetry={() => timeline.loadTimeline(1)}
            onSelectScrap={setSelectedScrapId}
          />
        )}
      </div>

      {selectedScrapId && (
        <ScrapDetailModal
          scrapId={selectedScrapId}
          onClose={() => setSelectedScrapId(null)}
          onDeleted={() => { setSelectedScrapId(null); loadScraps() }}
          onUpdated={loadScraps}
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
          onDone={() => { setShowTagModal(false); bulk.exitSelectMode(); loadScraps() }}
        />
      )}

      {showDuplicateModal && (
        <DuplicateModal
          onClose={() => setShowDuplicateModal(false)}
          onMerged={loadScraps}
        />
      )}

      {showAddModal && (
        <AddScrapModal
          onClose={() => setShowAddModal(false)}
          onAdded={loadScraps}
        />
      )}
      </div>{/* .scrap-main */}

      {/* Socrates 채팅 패널 (데스크톱: 사이드 패널, 모바일: 풀스크린 오버레이) */}
      {showChat && (
        isMobile ? (
          <div className="scrap-socrates-overlay">
            <div className="scrap-socrates-overlay__header">
              <h3>Socrates</h3>
              <button
                className="scrap-socrates-overlay__close"
                onClick={() => setShowChat(false)}
                type="button"
                aria-label="닫기"
              >
                <X size={20} />
              </button>
            </div>
            <SocratesPanel
              chat={socratesChat}
              className="socrates-panel--panel"
              onScrapClick={setSelectedScrapId}
              isPanelMode
              context={{ type: 'scrap' }}
            />
          </div>
        ) : (
          <div className="scrap-socrates-side" style={{ width: `${socratesVw}vw`, minWidth: `${socratesVw}vw` }}>
            <div className="resize-handle resize-handle--left" onMouseDown={onSocratesResize} />
            <div className="scrap-socrates-side__header">
              <Bot size={16} />
              <span>Socrates</span>
              <button
                className="scrap-socrates-side__close"
                onClick={() => setShowChat(false)}
                type="button"
                aria-label="패널 닫기"
              >
                <X size={16} />
              </button>
            </div>
            <SocratesPanel
              chat={socratesChat}
              className="socrates-panel--panel"
              onScrapClick={setSelectedScrapId}
              isPanelMode
              context={{ type: 'scrap' }}
            />
          </div>
        )
      )}
    </div>
  )
}
