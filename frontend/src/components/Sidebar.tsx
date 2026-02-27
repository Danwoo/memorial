import React, { useEffect, useCallback, useMemo } from 'react'
import { useResizePanel } from '../hooks/useResizePanel'
import type { ReactNode } from 'react'
import { NavLink } from 'react-router-dom'
import { useDemoMode } from '../contexts/DemoContext'
import {
  Calendar, BookOpen, PenLine, Network,
  Settings as SettingsIcon,
  LogOut,
} from 'lucide-react'
import type { User } from '../types'
import './Sidebar.css'

interface NavItem {
  to: string
  icon: ReactNode
  label: string
}

function getNavItems(prefix: string): NavItem[] {
  const items: NavItem[] = [
    { to: `${prefix}/calendar`,  icon: <Calendar size={20} />,  label: '캘린더' },
    { to: `${prefix}/diary`,     icon: <PenLine size={20} />,   label: '다이어리' },
    { to: `${prefix}/scraps`,    icon: <BookOpen size={20} />,  label: '스크랩' },
    { to: `${prefix}/mindmap`,   icon: <Network size={20} />,   label: '마인드맵' },
  ]
  if (!prefix) {
    items.push({ to: '/settings', icon: <SettingsIcon size={20} />, label: '설정' })
  }
  return items
}

interface SidebarProps {
  onLogout?: () => void
  user?: User | null
  mobileOpen?: boolean
  onMobileClose?: () => void
}

export default function Sidebar({ onLogout, user, mobileOpen, onMobileClose }: SidebarProps) {
  const { isDemoMode: isDemo } = useDemoMode()
  const prefix = isDemo ? '/demo' : ''
  const { width: sidebarW, onMouseDown: onSidebarResize } = useResizePanel(240, 160, 420, 'right', 'memoir-sidebar-width')

  // 모바일: Escape 키로 사이드바 닫기
  useEffect(() => {
    if (!mobileOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onMobileClose?.()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [mobileOpen, onMobileClose])

  const navItems = useMemo(() => getNavItems(prefix), [prefix])

  /** 아바타 표시 문자: 이름 첫 글자 또는 이메일 첫 글자 */
  const avatarInitial = user?.full_name
    ? user.full_name[0].toUpperCase()
    : user?.email[0].toUpperCase()

  const displayName = user?.full_name || user?.email.split('@')[0]

  // 모바일에서 네비게이션 클릭 시 사이드바 닫기
  const handleNavClick = useCallback(() => {
    onMobileClose?.()
  }, [onMobileClose])

  return (
    <>
    {mobileOpen && <div className="sidebar-backdrop" onClick={onMobileClose} />}
    <aside
      className={`sidebar ${mobileOpen ? 'sidebar--mobile-open' : ''}`}
      style={{ '--memoir-sidebar-w': `${sidebarW}px` } as React.CSSProperties}
    >
      <div className="resize-handle resize-handle--right" onMouseDown={onSidebarResize} />
      <div className="sidebar-header">
        <NavLink to={`${prefix}/calendar`} className="logo" onClick={handleNavClick}>
          <img src="/favicon.png" alt="" width={24} height={24} className="logo-icon" />
          <span className="logo-text">Memoir</span>
        </NavLink>
      </div>

      <nav className="sidebar-nav">
        {navItems.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
            onClick={handleNavClick}
          >
            <span className="nav-icon">{icon}</span>
            <span className="nav-label">{label}</span>
          </NavLink>
        ))}
      </nav>

      <div className="sidebar-footer">
        {user && (
          <div className="user-section">
            <div className="user-info">
              {user.avatar_url ? (
                <img src={user.avatar_url} alt="Profile" className="user-avatar" />
              ) : (
                <div className="user-avatar-placeholder">
                  {avatarInitial}
                </div>
              )}
              <div className="user-details">
                <span className="user-name">{displayName}</span>
                {user.full_name && (
                  <span className="user-email-sub">{user.email}</span>
                )}
              </div>
            </div>
            {onLogout && (
              <button className="logout-btn" onClick={onLogout} title="로그아웃" aria-label="로그아웃">
                <LogOut size={16} />
              </button>
            )}
          </div>
        )}
      </div>
    </aside>
    </>
  )
}
