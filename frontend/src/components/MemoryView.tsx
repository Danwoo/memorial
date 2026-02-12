import { useState, useEffect, useRef, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import {
  Globe, FileText, StickyNote, File, FolderOpen, Upload, Plus,
  SlidersHorizontal, SearchX, AlertCircle, CalendarX2,
} from 'lucide-react'
import type { Memory, MemoryCreatePayload, SourceType, SearchResult, TimelineData } from '../types'
import { fetchMemories, createMemory, uploadPdfMemory, searchMemories, fetchTimeline } from '../api'
import { getSourceIcon, getSimilarityLevel, formatDateKR, formatRelativeDate } from '../utils'
import './MemoryView.css'

const SOURCE_ICONS: Record<string, React.ReactNode> = {
  Globe: <Globe size={16} />,
  FileText: <FileText size={16} />,
  StickyNote: <StickyNote size={16} />,
  File: <File size={16} />,
}

function renderSourceIcon(type: string) {
  const iconName = getSourceIcon(type)
  return SOURCE_ICONS[iconName] ?? <File size={16} />
}

type MemoryTab = 'all' | 'timeline' | 'search'

export default function MemoryView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const initialTab = (searchParams.get('tab') as MemoryTab) || 'all'

  const [activeTab, setActiveTab] = useState<MemoryTab>(initialTab)

  // 전체 탭 상태
  const [memories, setMemories] = useState<Memory[]>([])
  const [isLoading, setIsLoading] = useState(false)

  // 추가 모달 상태
  const [showAddModal, setShowAddModal] = useState(false)
  const [newUrl, setNewUrl] = useState('')
  const [newNote, setNewNote] = useState('')
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [addType, setAddType] = useState<Extract<SourceType, 'WEB' | 'NOTE' | 'PDF'>>('WEB')

  // 타임라인 탭 상태
  const [timelineData, setTimelineData] = useState<TimelineData | null>(null)
  const [timelineLoading, setTimelineLoading] = useState(false)
  const [timelineLoadingMore, setTimelineLoadingMore] = useState(false)
  const [timelineError, setTimelineError] = useState<string | null>(null)
  const [timelinePage, setTimelinePage] = useState(1)
  const observerRef = useRef<IntersectionObserver | null>(null)
  const loadMoreRef = useRef<HTMLDivElement | null>(null)

  // 검색 탭 상태
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [daysFilter, setDaysFilter] = useState<string>('')

  const handleTabChange = (tab: MemoryTab) => {
    setActiveTab(tab)
    if (tab === 'all') {
      setSearchParams({})
    } else {
      setSearchParams({ tab })
    }
  }

  // ── 전체 탭 ──
  const loadMemories = async () => {
    setIsLoading(true)
    try {
      const data = await fetchMemories()
      setMemories(data.items || [])
    } catch (error) {
      console.error('Failed to load memories:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const addMemory = async () => {
    try {
      if (addType === 'PDF') {
        if (!pdfFile) return
        await uploadPdfMemory(pdfFile)
      } else {
        const payload: MemoryCreatePayload = addType === 'WEB'
          ? { sourceType: 'WEB', url: newUrl }
          : { sourceType: 'NOTE', content: newNote }
        await createMemory(payload)
      }
      setShowAddModal(false)
      setNewUrl('')
      setNewNote('')
      setPdfFile(null)
      loadMemories()
    } catch (error) {
      console.error('Failed to add memory:', error)
    }
  }

  useEffect(() => {
    loadMemories()
  }, [])

  // ── 타임라인 탭 ──
  const loadTimeline = useCallback(async (pageNum: number, append = false) => {
    try {
      if (pageNum === 1) setTimelineLoading(true)
      else setTimelineLoadingMore(true)

      const newData = await fetchTimeline(pageNum)

      if (append) {
        setTimelineData(prev => {
          if (!prev) return newData
          const merged = prev.timeline.map(g => ({
            ...g,
            memories: [...g.memories],
          }))
          for (const group of newData.timeline) {
            const existing = merged.find(g => g.date === group.date)
            if (existing) {
              existing.memories = [...existing.memories, ...group.memories]
            } else {
              merged.push(group)
            }
          }
          return { ...newData, timeline: merged }
        })
      } else {
        setTimelineData(newData)
      }
    } catch (err) {
      setTimelineError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setTimelineLoading(false)
      setTimelineLoadingMore(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab === 'timeline' && !timelineData) {
      loadTimeline(1)
    }
  }, [activeTab, timelineData, loadTimeline])

  // 무한 스크롤
  useEffect(() => {
    if (activeTab !== 'timeline') return
    if (observerRef.current) observerRef.current.disconnect()

    observerRef.current = new IntersectionObserver((entries) => {
      if (entries[0].isIntersecting && timelineData?.has_more && !timelineLoadingMore) {
        const nextPage = timelinePage + 1
        setTimelinePage(nextPage)
        loadTimeline(nextPage, true)
      }
    })

    if (loadMoreRef.current) {
      observerRef.current.observe(loadMoreRef.current)
    }

    return () => observerRef.current?.disconnect()
  }, [activeTab, timelineData?.has_more, timelineLoadingMore, timelinePage, loadTimeline])

  // ── 검색 탭 ──
  const handleSearch = async () => {
    if (!searchQuery.trim()) return
    setIsSearching(true)
    setHasSearched(true)
    try {
      const data = await searchMemories({
        q: searchQuery,
        source_type: sourceFilter || undefined,
        days: daysFilter || undefined,
      })
      setSearchResults(data.results || [])
    } catch (error) {
      console.error('Search failed:', error)
      setSearchResults([])
    } finally {
      setIsSearching(false)
    }
  }

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') handleSearch()
  }

  const clearFilters = () => {
    setSourceFilter('')
    setDaysFilter('')
  }

  const hasFilters = sourceFilter || daysFilter

  // ── 렌더링 ──
  const renderAllTab = () => (
    <div className="memory-grid">
      {isLoading ? (
        <div className="loading-state">로딩 중...</div>
      ) : memories.length === 0 ? (
        <div className="empty-state">
          <FolderOpen size={48} className="state-icon" />
          <h3>아직 저장된 기억이 없습니다</h3>
          <p>웹 페이지나 메모를 추가해보세요</p>
        </div>
      ) : (
        memories.map(memory => (
          <div key={memory.id} className="memory-card glass-card">
            <div className="memory-type-badge">
              {renderSourceIcon(memory.source_type)}
            </div>
            <h3 className="memory-title">{memory.title}</h3>
            {memory.summary && (
              <p className="memory-summary">{memory.summary}</p>
            )}
            <div className="memory-meta">
              <span>{new Date(memory.created_at).toLocaleDateString('ko-KR')}</span>
            </div>
          </div>
        ))
      )}
    </div>
  )

  const renderTimelineTab = () => {
    if (timelineLoading) {
      return (
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>타임라인 로딩 중...</p>
        </div>
      )
    }

    if (timelineError) {
      return (
        <div className="error-state">
          <AlertCircle size={48} className="state-icon" />
          <h3>오류 발생</h3>
          <p>{timelineError}</p>
          <button className="btn btn-primary" onClick={() => loadTimeline(1)}>
            다시 시도
          </button>
        </div>
      )
    }

    if (!timelineData || timelineData.timeline.length === 0) {
      return (
        <div className="empty-state">
          <CalendarX2 size={48} className="state-icon" />
          <h3>아직 메모리가 없습니다</h3>
          <p>새로운 지식을 저장해보세요!</p>
        </div>
      )
    }

    return (
      <div className="timeline-container">
        <div className="timeline-line"></div>
        {timelineData.timeline.map((group) => (
          <div key={group.date} className="timeline-group">
            <div className="timeline-date-marker">
              <span className="date-label">{formatRelativeDate(group.date)}</span>
            </div>
            <div className="timeline-items">
              {group.memories.map((memory) => (
                <div key={memory.id} className="timeline-item glass-card">
                  <div className="item-header">
                    <span className="source-icon">{renderSourceIcon(memory.source_type)}</span>
                    <h3 className="item-title">{memory.title}</h3>
                  </div>
                  {memory.summary && (
                    <p className="item-summary">{memory.summary}</p>
                  )}
                  {memory.tags && memory.tags.length > 0 && (
                    <div className="item-tags">
                      {memory.tags.slice(0, 3).map((tag, tagIdx) => (
                        <span key={tagIdx} className="tag">#{tag}</span>
                      ))}
                      {memory.tags.length > 3 && (
                        <span className="tag-more">+{memory.tags.length - 3}</span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        ))}
        <div ref={loadMoreRef} className="load-more-trigger">
          {timelineLoadingMore && (
            <div className="loading-more">
              <div className="loading-spinner small"></div>
              <span>더 불러오는 중...</span>
            </div>
          )}
        </div>
      </div>
    )
  }

  const renderSearchTab = () => (
    <div className="search-section">
      <div className="search-box glass-card">
        <div className="search-main">
          <input
            type="text"
            className="search-input"
            placeholder="예: 마케팅 전략에 대해 읽었던 글..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            onKeyDown={handleSearchKeyDown}
          />
          <button
            className="btn btn-secondary filter-toggle"
            onClick={() => setShowFilters(!showFilters)}
          >
            <SlidersHorizontal size={16} /> {hasFilters ? '필터 적용됨' : '필터'}
          </button>
          <button
            className="btn btn-primary search-btn"
            onClick={handleSearch}
            disabled={isSearching || !searchQuery.trim()}
          >
            {isSearching ? '검색 중...' : '검색'}
          </button>
        </div>

        {showFilters && (
          <div className="filter-panel">
            <div className="filter-group">
              <label>소스 타입</label>
              <select value={sourceFilter} onChange={e => setSourceFilter(e.target.value)}>
                <option value="">전체</option>
                <option value="WEB">웹페이지</option>
                <option value="PDF">PDF</option>
                <option value="NOTE">메모</option>
              </select>
            </div>
            <div className="filter-group">
              <label>기간</label>
              <select value={daysFilter} onChange={e => setDaysFilter(e.target.value)}>
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
        ) : hasSearched && searchResults.length === 0 ? (
          <div className="empty-state">
            <SearchX size={48} className="state-icon" />
            <h3>관련 기억을 찾지 못했습니다</h3>
            <p>다른 키워드로 검색해보세요</p>
          </div>
        ) : (
          searchResults.map(result => (
            <div key={result.id} className="result-card glass-card">
              <div className="result-header">
                <span className="source-badge">{renderSourceIcon(result.source_type)}</span>
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

  return (
    <div className="memory-view">
      <div className="memory-header">
        <div>
          <h1>Memories</h1>
          <p className="memory-subtitle">저장된 지식을 탐색하세요</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
          <Plus size={16} /> 추가
        </button>
      </div>

      <div className="memory-tabs">
        <button
          className={`memory-tab ${activeTab === 'all' ? 'active' : ''}`}
          onClick={() => handleTabChange('all')}
        >
          전체
        </button>
        <button
          className={`memory-tab ${activeTab === 'timeline' ? 'active' : ''}`}
          onClick={() => handleTabChange('timeline')}
        >
          타임라인
        </button>
        <button
          className={`memory-tab ${activeTab === 'search' ? 'active' : ''}`}
          onClick={() => handleTabChange('search')}
        >
          검색
        </button>
      </div>

      <div className="memory-tab-content">
        {activeTab === 'all' && renderAllTab()}
        {activeTab === 'timeline' && renderTimelineTab()}
        {activeTab === 'search' && renderSearchTab()}
      </div>

      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content glass-card" onClick={e => e.stopPropagation()}>
            <h2>새 메모리 추가</h2>

            <div className="modal-tabs">
              <button
                className={`tab ${addType === 'WEB' ? 'active' : ''}`}
                onClick={() => setAddType('WEB')}
              >
                <Globe size={16} /> 웹 URL
              </button>
              <button
                className={`tab ${addType === 'NOTE' ? 'active' : ''}`}
                onClick={() => setAddType('NOTE')}
              >
                <StickyNote size={16} /> 메모
              </button>
              <button
                className={`tab ${addType === 'PDF' ? 'active' : ''}`}
                onClick={() => setAddType('PDF')}
              >
                <FileText size={16} /> PDF
              </button>
            </div>

            {addType === 'WEB' ? (
              <input
                type="url"
                className="input"
                placeholder="https://example.com/article"
                value={newUrl}
                onChange={e => setNewUrl(e.target.value)}
              />
            ) : addType === 'NOTE' ? (
              <textarea
                className="input"
                placeholder="여기에 메모를 작성하세요..."
                value={newNote}
                onChange={e => setNewNote(e.target.value)}
                rows={5}
              />
            ) : (
              <div className="pdf-upload-area">
                <input
                  type="file"
                  accept=".pdf"
                  id="pdf-input"
                  onChange={e => setPdfFile(e.target.files?.[0] ?? null)}
                />
                <label htmlFor="pdf-input" className="pdf-drop-label">
                  {pdfFile ? pdfFile.name : <><Upload size={16} /> PDF 파일을 선택하세요 (최대 20MB)</>}
                </label>
              </div>
            )}

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
                취소
              </button>
              <button className="btn btn-primary" onClick={addMemory}>
                저장
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
