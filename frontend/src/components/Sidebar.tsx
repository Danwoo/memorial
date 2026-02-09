import { useState, useEffect } from 'react'
import { NavLink, useNavigate, useLocation } from 'react-router-dom'
import type { User, ChatSessionResponse } from '../types'
import { fetchChatSessions } from '../api'
import './Sidebar.css'

// ─── Navigation item definition ──────────────────────────────────────────────

interface NavItem {
  to: string
  icon: string
  label: string
}

const NAV_ITEMS: NavItem[] = [
  { to: '/chat',      icon: '💬', label: 'Chat' },
  { to: '/memories',  icon: '🧠', label: 'Memories' },
  { to: '/journal',   icon: '📝', label: 'Journal' },
  { to: '/search',    icon: '🔍', label: 'Search' },
  { to: '/graph',     icon: '🕸️', label: 'Graph' },
  { to: '/',          icon: '📊', label: 'Dashboard' },
  { to: '/timeline',  icon: '📅', label: 'Timeline' },
]

const MAX_SIDEBAR_SESSIONS = 8

// ─── Component ───────────────────────────────────────────────────────────────

interface SidebarProps {
  onLogout?: () => void
  user?: User | null
}

export default function Sidebar({ onLogout, user }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const [sessions, setSessions] = useState<ChatSessionResponse[]>([])
  const [showSessions, setShowSessions] = useState(true)

  const loadSessions = async () => {
    try {
      const data = await fetchChatSessions()
      setSessions(data)
    } catch {
      // Silently fail - sessions are a non-critical UI feature
    }
  }

  useEffect(() => {
    loadSessions()
  }, [])

  // Reload sessions when navigating to/from chat pages
  useEffect(() => {
    if (location.pathname.startsWith('/chat')) {
      loadSessions()
    }
  }, [location.pathname])

  const handleNewChat = () => {
    navigate('/chat', { state: { newSession: true } })
  }

  const isOnChatPage = location.pathname.startsWith('/chat')

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">📚</span>
          <span className="logo-text">Memoir</span>
        </div>
      </div>

      <nav className="sidebar-nav">
        {NAV_ITEMS.map(({ to, icon, label }) => (
          <NavLink
            key={to}
            to={to}
            end={to === '/' || to === '/chat'}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
          >
            <span className="nav-icon">{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}

        {/* Chat session list */}
        {isOnChatPage && sessions.length > 0 && (
          <div className="session-section">
            <button
              className="session-section-toggle"
              onClick={() => setShowSessions(!showSessions)}
            >
              <span>최근 대화</span>
              <span className="session-toggle-arrow">{showSessions ? '▾' : '▸'}</span>
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
        <button className="btn btn-primary new-chat-btn" onClick={handleNewChat}>
          <span>+ New Chat</span>
        </button>

        {user && (
          <div className="user-section">
            <div className="user-info">
              {user.avatar_url ? (
                <img src={user.avatar_url} alt="Profile" className="user-avatar" />
              ) : (
                <div className="user-avatar-placeholder">
                  {user.full_name ? user.full_name[0].toUpperCase() : user.email[0].toUpperCase()}
                </div>
              )}
              <div className="user-details">
                <span className="user-name">
                  {user.full_name || user.email.split('@')[0]}
                </span>
                {user.full_name && (
                  <span className="user-email-sub">{user.email}</span>
                )}
              </div>
            </div>
            {onLogout && (
              <button className="logout-btn" onClick={onLogout} title="Logout">
                🚪
              </button>
            )}
          </div>
        )}
      </div>
    </aside>
  )
}
