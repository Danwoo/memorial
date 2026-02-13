import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { Search, X, MessageSquare, BookOpen, FileText } from 'lucide-react'
import { searchMemories, fetchChatSessions } from '../api'
import type { SearchResult, ChatSessionResponse } from '../types'
import './CommandPalette.css'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

type ResultItem =
  | { kind: 'memory'; data: SearchResult }
  | { kind: 'session'; data: ChatSessionResponse }

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<ResultItem[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [activeIdx, setActiveIdx] = useState(0)

  // 열릴 때 입력창에 포커스
  useEffect(() => {
    if (isOpen) {
      setQuery('')
      setResults([])
      setActiveIdx(0)
      setTimeout(() => inputRef.current?.focus(), 50)
    }
  }, [isOpen])

  // Escape 닫기
  useEffect(() => {
    if (!isOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [isOpen, onClose])

  // 검색 디바운스
  useEffect(() => {
    if (!query.trim() || query.length < 2) {
      setResults([])
      return
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        const [memoryRes, sessionRes] = await Promise.allSettled([
          searchMemories({ q: query, limit: 8 }),
          fetchChatSessions(),
        ])

        const items: ResultItem[] = []

        if (memoryRes.status === 'fulfilled') {
          memoryRes.value.results.forEach((r) =>
            items.push({ kind: 'memory', data: r }),
          )
        }

        if (sessionRes.status === 'fulfilled') {
          const q = query.toLowerCase()
          sessionRes.value
            .filter((s) => s.title.toLowerCase().includes(q))
            .slice(0, 4)
            .forEach((s) => items.push({ kind: 'session', data: s }))
        }

        setResults(items)
        setActiveIdx(0)
      } catch {
        // 검색 실패 시 무시
      } finally {
        setIsSearching(false)
      }
    }, 300)

    return () => clearTimeout(timer)
  }, [query])

  const handleSelect = useCallback(
    (item: ResultItem) => {
      onClose()
      if (item.kind === 'memory') {
        navigate('/memories')
      } else if (item.kind === 'session') {
        navigate('/chat', { state: { sessionId: item.data.id } })
      }
    },
    [navigate, onClose],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown') {
        e.preventDefault()
        setActiveIdx((i) => Math.min(i + 1, results.length - 1))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setActiveIdx((i) => Math.max(i - 1, 0))
      } else if (e.key === 'Enter' && results[activeIdx]) {
        e.preventDefault()
        handleSelect(results[activeIdx])
      }
    },
    [results, activeIdx, handleSelect],
  )

  if (!isOpen) return null

  return (
    <div className="cmd-palette-overlay" onClick={onClose}>
      <div
        className="cmd-palette"
        role="dialog"
        aria-modal="true"
        aria-label="글로벌 검색"
        onClick={(e) => e.stopPropagation()}
      >
        {/* 검색 입력 */}
        <div className="cmd-palette__input-row">
          <Search size={18} className="cmd-palette__search-icon" />
          <input
            ref={inputRef}
            type="text"
            placeholder="메모리, 대화 검색..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="cmd-palette__input"
          />
          <kbd className="cmd-palette__kbd">ESC</kbd>
          <button className="cmd-palette__close" onClick={onClose} type="button">
            <X size={16} />
          </button>
        </div>

        {/* 결과 목록 */}
        {results.length > 0 && (
          <div className="cmd-palette__results">
            {results.map((item, idx) => (
              <button
                key={item.kind === 'memory' ? `m-${item.data.id}` : `s-${item.data.id}`}
                className={`cmd-palette__item ${idx === activeIdx ? 'active' : ''}`}
                onClick={() => handleSelect(item)}
                onMouseEnter={() => setActiveIdx(idx)}
                type="button"
              >
                <span className="cmd-palette__item-icon">
                  {item.kind === 'memory' ? (
                    item.data.source_type === 'NOTE' ? <FileText size={16} /> : <BookOpen size={16} />
                  ) : (
                    <MessageSquare size={16} />
                  )}
                </span>
                <div className="cmd-palette__item-content">
                  <span className="cmd-palette__item-title">
                    {item.kind === 'memory' ? item.data.title : item.data.title}
                  </span>
                  <span className="cmd-palette__item-meta">
                    {item.kind === 'memory'
                      ? (item.data.summary || '').slice(0, 60)
                      : new Date(item.data.created_at).toLocaleDateString('ko-KR')}
                  </span>
                </div>
                <span className="cmd-palette__item-badge">
                  {item.kind === 'memory' ? item.data.source_type : '대화'}
                </span>
              </button>
            ))}
          </div>
        )}

        {/* 빈 상태 */}
        {query.length >= 2 && results.length === 0 && !isSearching && (
          <div className="cmd-palette__empty">
            검색 결과가 없습니다.
          </div>
        )}

        {/* 로딩 */}
        {isSearching && (
          <div className="cmd-palette__loading">
            검색 중...
          </div>
        )}

        {/* 안내 */}
        {!query && (
          <div className="cmd-palette__hint">
            메모리, 대화 세션을 검색하세요
          </div>
        )}
      </div>
    </div>
  )
}
