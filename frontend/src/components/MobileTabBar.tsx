import { useState, useCallback, useEffect } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import {
  Calendar, BookOpen, PenLine, Network, MoreHorizontal,
  Settings as SettingsIcon, LogOut, X,
} from 'lucide-react'
import type { User } from '../types'
import './MobileTabBar.css'

interface MobileTabBarProps {
  user?: User | null
  onLogout?: () => void
  prefix?: string
}

export default function MobileTabBar({ user, onLogout, prefix = '' }: MobileTabBarProps) {
  const navigate = useNavigate()
  const [moreOpen, setMoreOpen] = useState(false)

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

  // Escape 키로 시트 닫기
  useEffect(() => {
    if (!moreOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') closeMore()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [moreOpen, closeMore])

  const tabs = [
    { to: `${prefix}/dashboard`, icon: Calendar, label: '캘린더' },
    { to: `${prefix}/journal`,   icon: PenLine,  label: '다이어리' },
    { to: `${prefix}/memories`,  icon: BookOpen,  label: '스크랩' },
    { to: `${prefix}/graph`,     icon: Network,   label: '마인드맵' },
  ] as const

  return (
    <>
      <nav className="mobile-tab-bar" aria-label="모바일 하단 탭">
        {tabs.map(({ to, icon: Icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `mobile-tab${isActive ? ' mobile-tab--active' : ''}`
            }
          >
            <Icon size={22} />
            <span className="mobile-tab__label">{label}</span>
          </NavLink>
        ))}

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
          <div className="mobile-more-sheet" role="dialog" aria-label="더보기 메뉴">
            <div className="mobile-more-header">
              <h3>더보기</h3>
              <button
                type="button"
                className="mobile-more-close"
                onClick={closeMore}
                aria-label="닫기"
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
