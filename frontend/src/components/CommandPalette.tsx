import { useState, useEffect, useCallback, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { demoPath } from '../utils/demoPath'
import { Search, X, MessageSquare, BookOpen, FileText, PenLine, Calendar, Settings, Network, Bot } from 'lucide-react'
import { searchScraps, fetchSocratesSessions, searchDiaries } from '../api'
import type { SearchResult, SocratesSessionResponse, DiaryEntry } from '../types'
import { useFocusTrap } from '../hooks/useFocusTrap'
import './CommandPalette.css'

interface CommandPaletteProps {
  isOpen: boolean
  onClose: () => void
}

type ResultItem =
  | { kind: 'scrap'; data: SearchResult }
  | { kind: 'session'; data: SocratesSessionResponse }
  | { kind: 'diary'; data: DiaryEntry }

interface ActionItem {
  kind: 'action'
  label: string
  path: string
  icon: React.ReactNode
  state?: Record<string, unknown>
}

const ACTION_COMMANDS: ActionItem[] = [
  { kind: 'action', label: '다이어리 열기', path: '/diary', icon: <PenLine size={16} /> },
  { kind: 'action', label: '스크랩 열기', path: '/scraps', icon: <BookOpen size={16} /> },
  { kind: 'action', label: '캘린더 열기', path: '/calendar', icon: <Calendar size={16} /> },
  { kind: 'action', label: '마인드맵 열기', path: '/mindmap', icon: <Network size={16} /> },
  { kind: 'action', label: 'Socrates 대화', path: '/diary', state: { openSocrates: true }, icon: <Bot size={16} /> },
  { kind: 'action', label: '설정 열기', path: '/settings', icon: <Settings size={16} /> },
]

type AnyItem = ResultItem | ActionItem

export default function CommandPalette({ isOpen, onClose }: CommandPaletteProps) {
  const navigate = useNavigate()
  const inputRef = useRef<HTMLInputElement>(null)
  const trapRef = useFocusTrap(isOpen)
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<AnyItem[]>([])
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
    // ">" 접두어: 액션 커맨드 필터
    if (query.startsWith('>')) {
      const q = query.slice(1).trim().toLowerCase()
      const filtered = q
        ? ACTION_COMMANDS.filter(a => a.label.toLowerCase().includes(q))
        : ACTION_COMMANDS
      setResults(filtered)
      setActiveIdx(0)
      return
    }

    if (!query.trim() || query.length < 2) {
      // 빈/짧은 쿼리 시 최근 세션 다시 표시
      fetchSocratesSessions()
        .then((sessions) => {
          setResults(sessions.slice(0, 6).map(s => ({ kind: 'session' as const, data: s })))
        })
        .catch(() => setResults([]))
      return
    }

    const timer = setTimeout(async () => {
      setIsSearching(true)
      try {
        // 필터 문법 파싱: tag:AI source:web
        const searchParams: Record<string, string> = {}
        const cleanQuery = query.replace(/\b(tag|source):(\S+)/gi, (_, key, val) => {
          searchParams[key.toLowerCase()] = val
          return ''
        }).trim()

        const scrapSearchParams: { q: string; limit?: number; source_type?: string; tags?: string } = {
          q: cleanQuery || query,
          limit: 15,
        }
        if (searchParams.source) scrapSearchParams.source_type = searchParams.source.toUpperCase()
        if (searchParams.tag) scrapSearchParams.tags = searchParams.tag

        const [scrapRes, sessionRes, diaryRes] = await Promise.allSettled([
          searchScraps(scrapSearchParams),
          fetchSocratesSessions(),
          searchDiaries(cleanQuery || query, 10),
        ])

        const items: ResultItem[] = []

        if (scrapRes.status === 'fulfilled') {
          scrapRes.value.results.forEach((r) =>
            items.push({ kind: 'scrap', data: r }),
          )
        }

        if (diaryRes.status === 'fulfilled') {
          diaryRes.value
            .slice(0, 10)
            .forEach((d) => items.push({ kind: 'diary', data: d }))
        }

        if (sessionRes.status === 'fulfilled') {
          const q = query.toLowerCase()
          sessionRes.value
            .filter((s) => !q || s.title.toLowerCase().includes(q) || (s.agent_type ?? '').toLowerCase().includes(q))
            .slice(0, 6)
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
    (item: AnyItem) => {
      onClose()
      if (item.kind === 'action') {
        navigate(demoPath(item.path), item.state ? { state: item.state } : undefined)
      } else if (item.kind === 'scrap') {
        navigate(demoPath('/scraps'), { state: { openMemoryId: item.data.id } })
      } else if (item.kind === 'diary') {
        const dateStr = item.data.created_at?.slice(0, 10)
        navigate(demoPath('/diary'), { state: { date: dateStr } })
      } else if (item.kind === 'session') {
        navigate(demoPath('/diary'), { state: { openSocrates: true, sessionId: item.data.id } })
      }
    },
    [navigate, onClose],
  )

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === 'ArrowDown' || (e.key === 'Tab' && !e.shiftKey)) {
        e.preventDefault()
        setActiveIdx((i) => (i + 1) % Math.max(results.length, 1))
      } else if (e.key === 'ArrowUp' || (e.key === 'Tab' && e.shiftKey)) {
        e.preventDefault()
        setActiveIdx((i) => (i - 1 + Math.max(results.length, 1)) % Math.max(results.length, 1))
      } else if (e.key === 'Enter' && results[activeIdx]) {
        e.preventDefault()
        handleSelect(results[activeIdx])
      }
    },
    [results, activeIdx, handleSelect],
  )

  if (!isOpen) return null

  return (
    <div className="cmd-palette-overlay" onClick={onClose} aria-label="검색 닫기" role="presentation">
      <div
        className="cmd-palette"
        role="dialog"
        aria-modal="true"
        aria-label="글로벌 검색"
        onClick={(e) => e.stopPropagation()}
        ref={trapRef}
      >
        {/* 검색 입력 */}
        <div className="cmd-palette__input-row">
          <Search size={18} className="cmd-palette__search-icon" />
          <input
            ref={inputRef}
            type="text"
            placeholder="검색... (tag:태그 / source:web / > 화면 이동)"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            className="cmd-palette__input"
          />
          <kbd className="cmd-palette__kbd">ESC</kbd>
          <button className="cmd-palette__close" onClick={onClose} type="button" aria-label="검색 닫기">
            <X size={16} />
          </button>
        </div>

        {/* 결과 목록 */}
        {results.length > 0 && (
          <div className="cmd-palette__results" role="listbox" aria-label="검색 결과" aria-live="polite">
            {query.startsWith('>') && (
              <div className="cmd-palette__section-header">화면 이동</div>
            )}
            {!query.trim() && (
              <div className="cmd-palette__section-header">최근 대화</div>
            )}
            {results.map((item, idx) => {
              if (item.kind === 'action') {
                return (
                  <button
                    key={item.label}
                    className={`cmd-palette__item ${idx === activeIdx ? 'active' : ''}`}
                    onClick={() => handleSelect(item)}
                    onMouseEnter={() => setActiveIdx(idx)}
                    type="button"
                  >
                    <span className="cmd-palette__item-icon">{item.icon}</span>
                    <div className="cmd-palette__item-content">
                      <span className="cmd-palette__item-title">{item.label}</span>
                    </div>
                    <span className="cmd-palette__item-badge">이동</span>
                  </button>
                )
              }
              const kindLabel: Record<string, string> = { scrap: '스크랩', diary: '다이어리', session: '대화' }
              const prevKind = idx > 0 ? results[idx - 1].kind : null
              const showHeader = !!query.trim() && item.kind !== prevKind
              const itemKey = item.kind === 'scrap' ? `sc-${item.data.id}` : item.kind === 'diary' ? `d-${item.data.id}` : `s-${item.data.id}`
              return (
                <div key={itemKey}>
                  {showHeader && (
                    <div className="cmd-palette__section-header">{kindLabel[item.kind]}</div>
                  )}
                  <button
                    className={`cmd-palette__item ${idx === activeIdx ? 'active' : ''}`}
                    onClick={() => handleSelect(item)}
                    onMouseEnter={() => setActiveIdx(idx)}
                    type="button"
                  >
                    <span className="cmd-palette__item-icon">
                      {item.kind === 'scrap' ? (
                        item.data.source_type === 'NOTE' ? <FileText size={16} /> : <BookOpen size={16} />
                      ) : item.kind === 'diary' ? (
                        <PenLine size={16} />
                      ) : (
                        <MessageSquare size={16} />
                      )}
                    </span>
                    <div className="cmd-palette__item-content">
                      {item.kind === 'diary' ? (
                        <span
                          className="cmd-palette__item-title"
                          dangerouslySetInnerHTML={{
                            __html: (() => {
                              const plain = item.data.content.replace(/<[^>]*>/g, '').slice(0, 50)
                              const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
                              return escaped ? plain.replace(new RegExp(`(${escaped})`, 'gi'), '<mark>$1</mark>') : plain
                            })(),
                          }}
                        />
                      ) : (
                        <span className="cmd-palette__item-title">{item.data.title}</span>
                      )}
                      <span className="cmd-palette__item-meta">
                        {item.kind === 'scrap'
                          ? (item.data.summary || '').slice(0, 60)
                          : item.kind === 'diary'
                            ? item.data.created_at?.slice(0, 10)
                            : new Date(item.data.created_at).toLocaleDateString('ko-KR')}
                      </span>
                    </div>
                    <span className="cmd-palette__item-badge">
                      {item.kind === 'scrap' ? item.data.source_type : item.kind === 'diary' ? '다이어리' : '대화'}
                    </span>
                  </button>
                </div>
              )
            })}
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
            검색 또는 <kbd className="cmd-palette__kbd">&gt;</kbd> 로 화면 이동 &middot; Ctrl+K
          </div>
        )}
      </div>
    </div>
  )
}
