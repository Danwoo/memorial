import { useState } from 'react'
import type { SearchResult } from '../types'
import { searchMemories } from '../api'
import { getSourceIcon, getSimilarityLevel, formatDateKR } from '../utils'
import './SearchView.css'

export default function SearchView() {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [searched, setSearched] = useState(false)

  // 검색 필터 상태 (소스 타입, 기간)
  const [showFilters, setShowFilters] = useState(false)
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [daysFilter, setDaysFilter] = useState<string>('')

  const handleSearch = async () => {
    if (!query.trim()) return

    setIsSearching(true)
    setSearched(true)

    try {
      const data = await searchMemories({
        q: query,
        source_type: sourceFilter || undefined,
        days: daysFilter || undefined,
      })
      setResults(data.results || [])
    } catch (error) {
      console.error('Search failed:', error)
      setResults([])
    } finally {
      setIsSearching(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch()
    }
  }

  const clearFilters = () => {
    setSourceFilter('')
    setDaysFilter('')
  }

  const hasFilters = sourceFilter || daysFilter

  return (
    <div className="search-view">
      <div className="search-header">
        <h1>🔍 의미 검색</h1>
        <p className="search-subtitle">자연어로 기억을 검색하세요</p>
      </div>

      <div className="search-box glass-card">
        <div className="search-main">
          <input
            type="text"
            className="search-input"
            placeholder="예: 마케팅 전략에 대해 읽었던 글..."
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button 
            className="btn btn-secondary filter-toggle"
            onClick={() => setShowFilters(!showFilters)}
          >
            ⚙️ {hasFilters ? '필터 적용됨' : '필터'}
          </button>
          <button 
            className="btn btn-primary search-btn"
            onClick={handleSearch}
            disabled={isSearching || !query.trim()}
          >
            {isSearching ? '검색 중...' : '검색'}
          </button>
        </div>
        
        {showFilters && (
          <div className="filter-panel">
            <div className="filter-group">
              <label>소스 타입</label>
              <select 
                value={sourceFilter} 
                onChange={e => setSourceFilter(e.target.value)}
              >
                <option value="">전체</option>
                <option value="WEB">🌐 웹페이지</option>
                <option value="PDF">📄 PDF</option>
                <option value="NOTE">📝 메모</option>
              </select>
            </div>
            
            <div className="filter-group">
              <label>기간</label>
              <select 
                value={daysFilter} 
                onChange={e => setDaysFilter(e.target.value)}
              >
                <option value="">전체 기간</option>
                <option value="7">최근 1주</option>
                <option value="30">최근 1개월</option>
                <option value="90">최근 3개월</option>
                <option value="365">최근 1년</option>
              </select>
            </div>
            
            {hasFilters && (
              <button className="btn btn-ghost clear-filters" onClick={clearFilters}>
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
        ) : searched && results.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">🤔</div>
            <h3>관련 기억을 찾지 못했습니다</h3>
            <p>다른 키워드로 검색해보세요</p>
          </div>
        ) : (
          results.map(result => (
            <div key={result.id} className="result-card glass-card">
              <div className="result-header">
                <span className="source-badge">{getSourceIcon(result.source_type)}</span>
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
                    {result.tags.slice(0, 3).map((tag, i) => (
                      <span key={i} className="tag">#{tag}</span>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
