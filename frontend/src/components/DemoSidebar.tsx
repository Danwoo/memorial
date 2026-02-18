import { useState, useEffect } from 'react'
import type { ReactNode } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import {
  MessageSquare, BookOpen, PenLine, Network, BarChart3,
  ChevronDown, ChevronRight, Plus,
} from 'lucide-react'
import { DEMO_SESSIONS } from '../data/demo-data'
import './Sidebar.css'

interface NavItem { to: string; icon: ReactNode; label: string }

const DEMO_NAV: NavItem[] = [
  { to: '/demo/chat',      icon: <MessageSquare size={20} />, label: '대화' },
  { to: '/demo/memories',  icon: <BookOpen size={20} />,      label: '기억' },
  { to: '/demo/journal',   icon: <PenLine size={20} />,       label: '저널' },
  { to: '/demo/graph',     icon: <Network size={20} />,       label: '그래프' },
  { to: '/demo/dashboard', icon: <BarChart3 size={20} />,     label: '대시보드' },
]

interface Props {
  mobileOpen?: boolean
  onMobileClose?: () => void
}

export default function DemoSidebar({ mobileOpen, onMobileClose }: Props) {
  const navigate = useNavigate()
  const location = useLocation()
  const [showSessions, setShowSessions] = useState(true)
  const isOnChat = location.pathname.startsWith('/demo/chat')

  // 모바일: Escape 키로 사이드바 닫기
  useEffect(() => {
    if (!mobileOpen) return
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onMobileClose?.()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [mobileOpen, onMobileClose])

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
          onClick={() => navigate('/demo/chat')}
          type="button"
        >
          <Plus size={18} />
          <span>새 대화</span>
        </button>

        {DEMO_NAV.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/demo/chat'}
            className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
            onClick={() => onMobileClose?.()}
          >
            <span className="nav-icon">{icon}</span>
            <span className="nav-label">{label}</span>
          </NavLink>
        ))}

        {isOnChat && (
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
                {DEMO_SESSIONS.map(s => (
                  <button
                    key={s.id}
                    className={`session-item ${location.pathname === `/demo/chat/${s.id}` ? 'active' : ''}`}
                    onClick={() => navigate(`/demo/chat/${s.id}`)}
                    title={s.title}
                  >
                    <span className="session-title">{s.title}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </nav>

      <div className="sidebar-footer">
        <div className="user-section">
          <div className="user-info">
            <div className="user-avatar-placeholder">D</div>
            <div className="user-details">
              <span className="user-name">Demo User</span>
            </div>
          </div>
        </div>
      </div>
    </aside>
    </>
  )
}
