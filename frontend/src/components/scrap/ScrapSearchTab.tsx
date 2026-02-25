import { SlidersHorizontal, SearchX } from 'lucide-react'
import type { SearchResult } from '../../types'
import { getSimilarityLevel, formatDateKR } from '../../utils'
import SourceIcon from '../shared/SourceIcon'
import EmptyState from '../EmptyState'

const MAX_VISIBLE_TAGS = 3

interface ScrapSearchTabProps {
  query: string
  onQueryChange: (query: string) => void
  results: SearchResult[]
  isSearching: boolean
  hasSearched: boolean
  showFilters: boolean
  onToggleFilters: () => void
  sourceFilter: string
  onSourceFilterChange: (filter: string) => void
  daysFilter: string
  onDaysFilterChange: (days: string) => void
  hasFilters: boolean
  onClearFilters: () => void
  onSearch: () => void
  onSelectScrap: (id: string) => void
}

export default function ScrapSearchTab({
  query,
  onQueryChange,
  results,
  isSearching,
  hasSearched,
  showFilters,
  onToggleFilters,
  sourceFilter,
  onSourceFilterChange,
  daysFilter,
  onDaysFilterChange,
  hasFilters,
  onClearFilters,
  onSearch,
  onSelectScrap,
}: ScrapSearchTabProps) {
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') onSearch()
  }

  return (
    <div className="search-section">
      <div className="search-box card">
        <div className="search-main">
          <input
            type="text"
            className="search-input"
            placeholder="예: 마케팅 전략에 대해 읽었던 글..."
            value={query}
            onChange={e => onQueryChange(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button
            className="btn btn-secondary filter-toggle"
            onClick={onToggleFilters}
          >
            <SlidersHorizontal size={16} /> {hasFilters ? '필터 적용됨' : '필터'}
          </button>
          <button
            className="btn btn-primary search-btn"
            onClick={onSearch}
            disabled={isSearching || !query.trim()}
          >
            {isSearching ? '검색 중...' : '검색'}
          </button>
        </div>

        {showFilters && (
          <div className="filter-panel">
            <div className="filter-group">
              <label>소스 타입</label>
              <select value={sourceFilter} onChange={e => onSourceFilterChange(e.target.value)}>
                <option value="">전체</option>
                <option value="WEB">웹페이지</option>
                <option value="PDF">PDF</option>
                <option value="NOTE">메모</option>
              </select>
            </div>
            <div className="filter-group">
              <label>기간</label>
              <select value={daysFilter} onChange={e => onDaysFilterChange(e.target.value)}>
                <option value="">전체 기간</option>
                <option value="7">최근 1주</option>
                <option value="30">최근 1개월</option>
                <option value="90">최근 3개월</option>
                <option value="365">최근 1년</option>
              </select>
            </div>
            {hasFilters && (
              <button className="btn btn-ghost clear-filters" onClick={onClearFilters}>
                필터 초기화
              </button>
            )}
          </div>
        )}
      </div>

      <div className="search-results">
        {isSearching ? (
          <div className="loading-state">
            <div className="loading-spinner"></div>
            <p>AI가 비슷한 기억을 찾고 있습니다...</p>
          </div>
        ) : hasSearched && results.length === 0 ? (
          <EmptyState
            icon={<SearchX size={48} />}
            title="관련 기억을 찾지 못했습니다"
            description="다른 키워드로 검색해보세요"
          />
        ) : (
          results.map(result => (
            <button key={result.id} className="result-card card" onClick={() => onSelectScrap(result.id)} style={{ cursor: 'pointer', textAlign: 'left', width: '100%' }}>
              <div className="result-header">
                <span className="source-badge"><SourceIcon type={result.source_type} /></span>
                <h3 className="result-title">{result.title}</h3>
                <span className={`similarity-badge ${getSimilarityLevel(result.similarity)}`}>
                  {Math.round(result.similarity * 100)}% 일치
                </span>
              </div>
              {result.summary ? (
                <p className="result-summary">{result.summary}</p>
              ) : (
                <p className="result-content">{result.content}</p>
              )}
              <div className="result-meta">
                {result.created_at && (
                  <span className="result-date">{formatDateKR(result.created_at)}</span>
                )}
                {result.tags && result.tags.length > 0 && (
                  <div className="result-tags">
                    {result.tags.slice(0, MAX_VISIBLE_TAGS).map((tag, i) => (
                      <span key={i} className="tag">#{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            </button>
          ))
        )}
      </div>
    </div>
  )
}
