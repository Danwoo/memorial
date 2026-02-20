import { CheckSquare, Square, FolderOpen, ArrowUpDown } from 'lucide-react'
import type { Memory } from '../../types'
import { timeAgo } from '../../utils'
import SourceIcon from '../shared/SourceIcon'
import EmptyState from '../EmptyState'

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
}: MemoryAllTabProps) {
  return (
    <div className="memory-all-tab">
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
      <div className="memory-grid">
        {selectMode && memories.length > 0 && (
          <div className="select-header">
            <button className="select-all-btn" onClick={onToggleSelectAll}>
              {selectedIds.size === memories.length
                ? <CheckSquare size={18} />
                : <Square size={18} />}
              <span>전체 선택 ({selectedIds.size}/{memories.length})</span>
            </button>
          </div>
        )}
        {isLoading ? (
          <div className="memory-skeleton-list">
            {Array.from({ length: 5 }, (_, i) => (
              <div key={i} className="skeleton skeleton-card" />
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
              className={`memory-card card ${selectMode && selectedIds.has(memory.id) ? 'selected' : ''}`}
              onClick={(e) => {
                if (selectMode) {
                  onToggleSelect(memory.id, index, e.shiftKey)
                } else {
                  onSelectMemory(memory.id)
                }
              }}
              style={{ cursor: 'pointer' }}
              aria-label={`메모리: ${memory.title}`}
            >
              {selectMode && (
                <div className="card-checkbox">
                  {selectedIds.has(memory.id)
                    ? <CheckSquare size={20} />
                    : <Square size={20} />}
                </div>
              )}
              <div className="memory-type-badge">
                <SourceIcon type={memory.source_type} />
              </div>
              <h3 className="memory-title">{memory.title}</h3>
              {memory.summary && (
                <p className="memory-summary">{memory.summary}</p>
              )}
              {memory.tags && memory.tags.length > 0 && (
                <div className="memory-tags">
                  {memory.tags.slice(0, 3).map((tag) => (
                    <span key={tag} className="memory-tag-chip">{tag}</span>
                  ))}
                  {memory.tags.length > 3 && (
                    <span className="memory-tag-chip memory-tag-chip--more">+{memory.tags.length - 3}</span>
                  )}
                </div>
              )}
              <div className="memory-meta">
                <span>{timeAgo(memory.created_at)}</span>
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
