import { useState, useEffect, useCallback } from 'react'
import type { ReactNode } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  MessageSquare, BookOpen, PenLine, Network, BarChart3,
  Settings as SettingsIcon,
  LogOut, ChevronDown, ChevronRight, Plus,
} from 'lucide-react'
import type { User, ChatSessionResponse } from '../types'
import { fetchChatSessions } from '../api'
import './Sidebar.css'

interface NavItem {
  to: string
  icon: ReactNode
  label: string
}

const NAV_ITEMS: NavItem[] = [
  { to: '/chat',      icon: <MessageSquare size={20} />, label: '대화' },
  { to: '/memories',  icon: <BookOpen size={20} />,      label: '기억' },
  { to: '/journal',   icon: <PenLine size={20} />,       label: '저널' },
  { to: '/graph',     icon: <Network size={20} />,       label: '그래프' },
  { to: '/dashboard', icon: <BarChart3 size={20} />,     label: '대시보드' },
  { to: '/settings',  icon: <SettingsIcon size={20} />,  label: '설정' },
]

// 사이드바에 표시할 최대 세션 수
const MAX_SIDEBAR_SESSIONS = 8

interface SidebarProps {
  onLogout?: () => void
  user?: User | null
  mobileOpen?: boolean
  onMobileClose?: () => void
}

export default function Sidebar({ onLogout, user, mobileOpen, onMobileClose }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [sessions, setSessions] = useState<ChatSessionResponse[]>([])
  const [showSessions, setShowSessions] = useState(true)

  const loadSessions = useCallback(async () => {
    try {
      const data = await fetchChatSessions()
      setSessions(data)
    } catch {
      // 세션 목록은 비필수 UI 요소이므로 실패 시 무시
    }
  }, [])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  // 채팅 페이지 진입 시 세션 목록 새로고침
  useEffect(() => {
    if (location.pathname.startsWith('/chat')) {
      loadSessions()
    }
  }, [location.pathname, loadSessions])

  // 세션 제목 자동 생성 시 목록 새로고침
  useEffect(() => {
    const handler = () => loadSessions()
    window.addEventListener('session-title-updated', handler)
    return () => window.removeEventListener('session-title-updated', handler)
  }, [loadSessions])

  const isOnChatPage = location.pathname.startsWith('/chat')

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
    <aside className={`sidebar ${mobileOpen ? 'sidebar--mobile-open' : ''}`}>
      <div className="sidebar-header">
        <div className="logo">
          <img src="/favicon.png" alt="" width={24} height={24} className="logo-icon" />
          <span className="logo-text">Memoir</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        <button
          className="new-chat-btn"
          onClick={() => navigate('/chat', { state: { newSession: true } })}
          type="button"
        >
          <Plus size={18} />
          <span>새 대화</span>
        </button>

        {NAV_ITEMS.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/chat'}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
            onClick={handleNavClick}
          >
            <span className="nav-icon">{icon}</span>
            <span className="nav-label">{label}</span>
          </NavLink>
        ))}

        {/* 채팅 세션 목록 */}
        {isOnChatPage && sessions.length > 0 && (
          <div className="session-section">
            <button
              className="session-section-toggle"
              onClick={() => setShowSessions(!showSessions)}
              aria-expanded={showSessions}
            >
              <span>최근 대화</span>
              <span className="session-toggle-arrow">
                {showSessions ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
              </span>
            </button>

            {showSessions && (
              <div className="session-list">
                {sessions.slice(0, MAX_SIDEBAR_SESSIONS).map(session => {
                  const isActive = location.pathname === `/chat/${session.id}`
                  return (
                    <button
                      key={session.id}
                      className={`session-item ${isActive ? 'active' : ''}`}
                      onClick={() => navigate(`/chat/${session.id}`)}
                      title={session.title}
                    >
                      <span className="session-title">{session.title}</span>
                    </button>
                  )
                })}
              </div>
            )}
          </div>
        )}
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
