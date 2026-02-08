import { NavLink, useNavigate } from 'react-router-dom'
import type { User } from '../types'
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

// ─── Component ───────────────────────────────────────────────────────────────

interface SidebarProps {
  onLogout?: () => void
  user?: User | null
}

export default function Sidebar({ onLogout, user }: SidebarProps) {
  const navigate = useNavigate()

  const handleNewChat = () => {
    // Navigate to /chat without session state to start fresh
    navigate('/chat', { state: { newSession: true } })
  }

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
            end={to === '/'}
            className={({ isActive }) =>
              `nav-item ${isActive ? 'active' : ''}`
            }
          >
            <span className="nav-icon">{icon}</span>
            <span>{label}</span>
          </NavLink>
        ))}
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
