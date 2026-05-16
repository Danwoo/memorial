import { useState, useCallback, useEffect, useRef } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  Calendar, BookOpen, PenLine, Network, Search, MoreHorizontal,
  Settings as SettingsIcon, LogOut, X,
} from 'lucide-react'
import type { User } from '../types'
import './MobileTabBar.css'

interface MobileTabBarProps {
  user?: User | null
  onLogout?: () => void
  prefix?: string
  onOpenSearch?: () => void
}

export default function MobileTabBar({ user, onLogout, prefix = '', onOpenSearch }: MobileTabBarProps) {
  const navigate = useNavigate()
  const [moreOpen, setMoreOpen] = useState(false)
  const sheetRef = useRef<HTMLDivElement>(null)
  const closeButtonRef = useRef<HTMLButtonElement>(null)

  /** 더보기 시트 토글 */
  const toggleMore = useCallback(() => {
    setMoreOpen(prev => !prev)
  }, [])

  /** 더보기 시트 닫기 */
  const closeMore = useCallback(() => {
    setMoreOpen(false)
  }, [])

  /** 더보기 항목 클릭 → 이동 후 시트 닫기 */
  const handleMoreNav = useCallback((path: string) => {
    navigate(path)
    closeMore()
  }, [navigate, closeMore])

  /** 로그아웃 클릭 */
  const handleLogout = useCallback(() => {
    closeMore()
    onLogout?.()
  }, [closeMore, onLogout])

  // 시트 열릴 때 닫기 버튼에 포커스
  useEffect(() => {
    if (moreOpen) {
      setTimeout(() => closeButtonRef.current?.focus(), 50)
    }
  }, [moreOpen])

  // Escape 키 + 포커스 트랩
  useEffect(() => {
    if (!moreOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        closeMore()
        return
      }
      if (e.key === 'Tab' && sheetRef.current) {
        const focusable = sheetRef.current.querySelectorAll<HTMLElement>(
          'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
        )
        const first = focusable[0]
        const last = focusable[focusable.length - 1]
        if (e.shiftKey ? document.activeElement === first : document.activeElement === last) {
          e.preventDefault();
          (e.shiftKey ? last : first).focus()
        }
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [moreOpen, closeMore])

  const tabs = [
    { to: `${prefix}/calendar`,  icon: Calendar, label: '캘린더',   route: 'calendar' },
    { to: `${prefix}/diary`,     icon: PenLine,  label: '다이어리', route: 'diary' },
    { to: `${prefix}/scraps`,    icon: BookOpen,  label: '스크랩',   route: 'scraps' },
    { to: `${prefix}/mindmap`,   icon: Network,   label: '마인드맵', route: 'mindmap' },
  ] as const

  return (
    <>
      <nav className="mobile-tab-bar" aria-label="모바일 하단 탭">
        {tabs.map(({ to, icon: Icon, label, route }) => (
          <NavLink
            key={to}
            to={to}
            data-route={route}
            className={({ isActive }) =>
              `mobile-tab${isActive ? ' mobile-tab--active' : ''}`
            }
          >
            <Icon size={22} />
            <span className="mobile-tab__label">{label}</span>
          </NavLink>
        ))}

        {onOpenSearch && (
          <button
            type="button"
            className="mobile-tab mobile-tab--search"
            onClick={onOpenSearch}
            aria-label="검색"
          >
            <Search size={22} />
            <span className="mobile-tab__label">검색</span>
          </button>
        )}

        <button
          type="button"
          className={`mobile-tab${moreOpen ? ' mobile-tab--active' : ''}`}
          onClick={toggleMore}
          aria-label="더보기 메뉴"
          aria-expanded={moreOpen}
        >
          <MoreHorizontal size={22} />
          <span className="mobile-tab__label">더보기</span>
        </button>
      </nav>

      {/* 더보기 바텀시트 */}
      {moreOpen && (
        <>
          <div className="mobile-more-backdrop" onClick={closeMore} />
          <div className="mobile-more-sheet" role="dialog" aria-modal="true" aria-label="더보기 메뉴" ref={sheetRef}>
            <div className="mobile-more-header">
              <h3>더보기</h3>
              <button
                type="button"
                className="mobile-more-close"
                onClick={closeMore}
                aria-label="닫기"
                ref={closeButtonRef}
              >
                <X size={20} />
              </button>
            </div>

            <div className="mobile-more-nav">
              {!prefix && (
                <button
                  type="button"
                  className="mobile-more-item"
                  onClick={() => handleMoreNav('/settings')}
                >
                  <SettingsIcon size={20} />
                  <span>설정</span>
                </button>
              )}

              {user && onLogout && (
                <button
                  type="button"
                  className="mobile-more-item mobile-more-item--danger"
                  onClick={handleLogout}
                >
                  <LogOut size={20} />
                  <span>로그아웃</span>
                </button>
              )}
            </div>
          </div>
        </>
      )}
    </>
  )
}
