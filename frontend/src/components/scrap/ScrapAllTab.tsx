import { CheckSquare, Square, FolderOpen, ArrowUpDown, Search, X } from 'lucide-react'
import type { Scrap } from '../../types'
import { timeAgo } from '../../utils'
import SourceIcon from '../shared/SourceIcon'
import EmptyState from '../EmptyState'
import { useIsMobile } from '../../hooks/useMediaQuery'

interface ScrapAllTabProps {
  scraps: Scrap[]
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
  onSelectScrap: (id: string) => void
  page: number
  totalPages: number
  total: number
  searchQuery: string
  onSearchChange: (q: string) => void
  onSearchCommit: () => void
  onSearchClear: () => void
  onPageChange: (page: number) => void
  onAddClick?: () => void
  dateFrom?: string
  dateTo?: string
  onDateFromChange?: (v: string) => void
  onDateToChange?: (v: string) => void
  tagFilter?: string[]
  onTagFilterChange?: (tags: string[]) => void
  availableTags?: string[]
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
    <div className="scrap-pagination">
      <button
        className="scrap-pagination__btn"
        onClick={() => onPageChange(page - 1)}
        disabled={page <= 1}
        aria-label="이전 페이지"
      >
        &lt;
      </button>
      {pages.map((p, idx) =>
        p === 'ellipsis' ? (
          <span key={`e-${idx}`} className="scrap-pagination__ellipsis">&hellip;</span>
        ) : (
          <button
            key={p}
            className={`scrap-pagination__btn ${p === page ? 'scrap-pagination__btn--active' : ''}`}
            onClick={() => onPageChange(p)}
            aria-current={p === page ? 'page' : undefined}
          >
            {p}
          </button>
        ),
      )}
      <button
        className="scrap-pagination__btn"
        onClick={() => onPageChange(page + 1)}
        disabled={page >= totalPages}
        aria-label="다음 페이지"
      >
        &gt;
      </button>
    </div>
  )
}

export default function ScrapAllTab({
  scraps,
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
  onSelectScrap,
  page,
  totalPages,
  total,
  searchQuery,
  onSearchChange,
  onSearchCommit,
  onSearchClear,
  onPageChange,
  onAddClick,
  dateFrom,
  dateTo,
  onDateFromChange,
  onDateToChange,
  tagFilter = [],
  onTagFilterChange,
  availableTags = [],
}: ScrapAllTabProps) {
  const isMobile = useIsMobile()

  return (
    <div className="scrap-all-tab">
      {/* 검색바 */}
      <div className="scrap-search-bar">
        <Search size={16} className="scrap-search-bar__icon" />
        <input
          type="text"
          className="scrap-search-bar__input"
          placeholder="제목, 태그로 검색..."
          value={searchQuery}
          onChange={e => onSearchChange(e.target.value)}
          onKeyDown={e => { if (e.key === 'Enter') onSearchCommit() }}
        />
        {searchQuery && (
          <button className="scrap-search-bar__clear" onClick={onSearchClear} aria-label="검색 초기화">
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

      {/* 날짜 범위 + 태그 필터 */}
      {(onDateFromChange || (availableTags.length > 0 && onTagFilterChange)) && (
        <div className="advanced-filter-bar">
          {onDateFromChange && onDateToChange && (
            <div className="date-range-filter">
              <input
                type="date"
                className="date-input"
                value={dateFrom || ''}
                onChange={e => onDateFromChange(e.target.value)}
              />
              <span className="date-separator">~</span>
              <input
                type="date"
                className="date-input"
                value={dateTo || ''}
                onChange={e => onDateToChange(e.target.value)}
              />
              {(dateFrom || dateTo) && (
                <button
                  className="filter-chip"
                  onClick={() => { onDateFromChange(''); onDateToChange('') }}
                  aria-label="날짜 필터 초기화"
                >
                  <X size={12} />
                </button>
              )}
            </div>
          )}
          {availableTags.length > 0 && onTagFilterChange && (
            <div className="tag-filter-chips">
              {availableTags.slice(0, 10).map(tag => (
                <button
                  key={tag}
                  className={`filter-chip filter-chip--tag ${tagFilter.includes(tag) ? 'active' : ''}`}
                  onClick={() => {
                    if (tagFilter.includes(tag)) {
                      onTagFilterChange(tagFilter.filter(t => t !== tag))
                    } else {
                      onTagFilterChange([...tagFilter, tag])
                    }
                  }}
                >
                  #{tag}
                </button>
              ))}
              {tagFilter.length > 0 && (
                <button className="filter-chip" onClick={() => onTagFilterChange([])}>
                  초기화
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* 선택 모드 헤더 */}
      {selectMode && scraps.length > 0 && (
        <div className="scrap-list-select-header">
          <button className="select-all-btn" onClick={onToggleSelectAll}>
            {selectedIds.size === scraps.length
              ? <CheckSquare size={18} />
              : <Square size={18} />}
            <span>전체 선택 ({selectedIds.size}/{scraps.length})</span>
          </button>
        </div>
      )}

      {/* 리스트 뷰 */}
      <div className="scrap-list">
        {isLoading ? (
          <div className="scrap-list-loading">
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="skeleton skeleton-row" />
            ))}
          </div>
        ) : scraps.length === 0 ? (
          <EmptyState
            icon={<FolderOpen size={48} />}
            title="아직 저장된 스크랩이 없습니다"
            description="웹 페이지나 메모를 추가해보세요"
            ctaLabel="+ 스크랩 추가"
            onCtaClick={onAddClick}
          />
        ) : (
          scraps.map((scrap, index) => (
            <button
              key={scrap.id}
              className={`scrap-list-row ${selectMode ? 'scrap-list-row--select-mode' : ''} ${selectMode && selectedIds.has(scrap.id) ? 'scrap-list-row--selected' : ''}`}
              onClick={(e) => {
                if (selectMode) {
                  onToggleSelect(scrap.id, index, e.shiftKey)
                } else {
                  onSelectScrap(scrap.id)
                }
              }}
              aria-label={`스크랩: ${scrap.title}`}
            >
              {selectMode && (
                <div className="scrap-list-row__checkbox">
                  {selectedIds.has(scrap.id)
                    ? <CheckSquare size={18} />
                    : <Square size={18} />}
                </div>
              )}
              <div className="scrap-list-row__icon">
                <SourceIcon type={scrap.source_type} />
              </div>
              <div className="scrap-list-row__title">{scrap.title}</div>
              {!isMobile && scrap.tags && scrap.tags.length > 0 && (
                <div className="scrap-list-row__tags">
                  {scrap.tags.slice(0, 2).map(tag => (
                    <span key={tag} className="scrap-tag-chip">{tag}</span>
                  ))}
                  {scrap.tags.length > 2 && (
                    <span className="scrap-tag-chip scrap-tag-chip--more">+{scrap.tags.length - 2}</span>
                  )}
                </div>
              )}
              <div className="scrap-list-row__date">{timeAgo(scrap.created_at)}</div>
            </button>
          ))
        )}
      </div>

      {/* 총 개수 + 페이지네이션 */}
      {!isLoading && total > 0 && (
        <div className="scrap-list-footer">
          <span className="scrap-list-footer__total">총 {total}개</span>
          <Pagination page={page} totalPages={totalPages} onPageChange={onPageChange} />
        </div>
      )}
    </div>
  )
}
