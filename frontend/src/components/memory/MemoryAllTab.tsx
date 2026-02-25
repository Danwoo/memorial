import { CheckSquare, Square, FolderOpen, ArrowUpDown, Search, X } from 'lucide-react'
import type { Memory } from '../../types'
import { timeAgo } from '../../utils'
import SourceIcon from '../shared/SourceIcon'
import EmptyState from '../EmptyState'
import { useIsMobile } from '../../hooks/useMediaQuery'

interface MemoryAllTabProps {
  memories: Memory[]
  isLoading: boolean
  sortBy: string
  sortOrder: string
  sourceFilter: string
  onSortChange: (sortBy: 'created_at' | 'updated_at' | 'title', sortOrder: 'asc' | 'desc') => void
  onSourceFilterChange: (filter: string) => void
  selectMode: boolean
  selectedIds: Set<string>
  onToggleSelect: (id: string, index: number, shiftKey: boolean) => void
  onToggleSelectAll: () => void
  onSelectMemory: (id: string) => void
  page: number
  totalPages: number
  total: number
  searchQuery: string
  onSearchChange: (q: string) => void
  onSearchCommit: () => void
  onSearchClear: () => void
  onPageChange: (page: number) => void
}

function Pagination({ page, totalPages, onPageChange }: { page: number; totalPages: number; onPageChange: (n: number) => void }) {
  if (totalPages <= 1) return null

  const pages: (number | 'ellipsis')[] = []
  const delta = 2

  for (let i = 1; i <= totalPages; i++) {
    if (i === 1 || i === totalPages || (i >= page - delta && i <= page + delta)) {
      pages.push(i)
    } else if (pages[pages.length - 1] !== 'ellipsis') {
      pages.push('ellipsis')
    }
  }

  return (
    <div className="memory-pagination">
      <button
        className="memory-pagination__btn"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        aria-label="이전 페이지"
      >
        &lt;
      </button>
      {pages.map((p, idx) =>
        p === 'ellipsis' ? (
          <span key={`e-${idx}`} className="memory-pagination__ellipsis">&hellip;</span>
        ) : (
          <button
            key={p}
            className={`memory-pagination__btn ${p === page ? 'memory-pagination__btn--active' : ''}`}
            onClick={() => onPageChange(p)}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        ),
      )}
      <button
        className="memory-pagination__btn"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        aria-label="다음 페이지"
      >
        &gt;
      </button>
    </div>
  )
}

export default function MemoryAllTab({
  memories,
  isLoading,
  sortBy,
  sortOrder,
  sourceFilter,
  onSortChange,
  onSourceFilterChange,
  selectMode,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  onSelectMemory,
  page,
  totalPages,
  total,
  searchQuery,
  onSearchChange,
  onSearchCommit,
  onSearchClear,
  onPageChange,
}: MemoryAllTabProps) {
  const isMobile = useIsMobile()

  return (
    <div className="memory-all-tab">
      {/* 검색바 */}
      <div className="memory-search-bar">
        <Search size={16} className="memory-search-bar__icon" />
        <input
          type="text"
          className="memory-search-bar__input"
          placeholder="제목, 태그로 검색..."
          value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') onSearchCommit() }}
        />
        {searchQuery && (
          <button className="memory-search-bar__clear" onClick={onSearchClear} aria-label="검색 초기화">
            <X size={16} />
          </button>
        )}
      </div>

      {/* 필터 바 */}
      <div className="filter-bar">
        <div className="filter-bar-chips">
          {['', 'WEB', 'PDF', 'NOTE'].map(st => (
            <button
              key={st}
              className={`filter-chip ${sourceFilter === st ? 'active' : ''}`}
              onClick={() => onSourceFilterChange(st)}
            >
              {st === '' ? '전체' : st === 'WEB' ? '웹' : st === 'PDF' ? 'PDF' : '메모'}
            </button>
          ))}
        </div>
        <div className="filter-bar-sort">
          <ArrowUpDown size={14} />
          <select
            value={`${sortBy}:${sortOrder}`}
            onChange={e => {
              const [sb, so] = e.target.value.split(':')
              onSortChange(
                sb as 'created_at' | 'updated_at' | 'title',
                so as 'asc' | 'desc',
              )
            }}
          >
            <option value="created_at:desc">최신순</option>
            <option value="created_at:asc">오래된순</option>
            <option value="title:asc">제목 A-Z</option>
            <option value="title:desc">제목 Z-A</option>
            <option value="updated_at:desc">최근 수정순</option>
          </select>
        </div>
      </div>

      {/* 선택 모드 헤더 */}
      {selectMode && memories.length > 0 && (
        <div className="memory-list-select-header">
          <button className="select-all-btn" onClick={onToggleSelectAll}>
            {selectedIds.size === memories.length
              ? <CheckSquare size={18} />
              : <Square size={18} />}
            <span>전체 선택 ({selectedIds.size}/{memories.length})</span>
          </button>
        </div>
      )}

      {/* 리스트 뷰 */}
      <div className="memory-list">
        {isLoading ? (
          <div className="memory-list-loading">
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="skeleton skeleton-row" />
            ))}
          </div>
        ) : memories.length === 0 ? (
          <EmptyState
            icon={<FolderOpen size={48} />}
            title="아직 저장된 기억이 없습니다"
            description="웹 페이지나 메모를 추가해보세요"
          />
        ) : (
          memories.map((memory, index) => (
            <button
              key={memory.id}
              className={`memory-list-row ${selectMode ? 'memory-list-row--select-mode' : ''} ${selectMode && selectedIds.has(memory.id) ? 'memory-list-row--selected' : ''}`}
              onClick={(e) => {
                if (selectMode) {
                  onToggleSelect(memory.id, index, e.shiftKey)
                } else {
                  onSelectMemory(memory.id)
                }
              }}
              aria-label={`메모리: ${memory.title}`}
            >
              {selectMode && (
                <div className="memory-list-row__checkbox">
                  {selectedIds.has(memory.id)
                    ? <CheckSquare size={18} />
                    : <Square size={18} />}
                </div>
              )}
              <div className="memory-list-row__icon">
                <SourceIcon type={memory.source_type} />
              </div>
              <div className="memory-list-row__title">{memory.title}</div>
              {!isMobile && memory.tags && memory.tags.length > 0 && (
                <div className="memory-list-row__tags">
                  {memory.tags.slice(0, 2).map(tag => (
                    <span key={tag} className="memory-tag-chip">{tag}</span>
                  ))}
                  {memory.tags.length > 2 && (
                    <span className="memory-tag-chip memory-tag-chip--more">+{memory.tags.length - 2}</span>
                  )}
                </div>
              )}
              <div className="memory-list-row__date">{timeAgo(memory.created_at)}</div>
            </button>
          ))
        )}
      </div>

      {/* 총 개수 + 페이지네이션 */}
      {!isLoading && total > 0 && (
        <div className="memory-list-footer">
          <span className="memory-list-footer__total">총 {total}개</span>
          <Pagination page={page} totalPages={totalPages} onPageChange={onPageChange} />
        </div>
      )}
    </div>
  )
}
