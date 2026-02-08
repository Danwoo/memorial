import './Sidebar.css'

interface SidebarProps {
  currentView: 'chat' | 'memories' | 'graph' | 'search' | 'dashboard' | 'timeline' | 'journal'
  onViewChange: (view: 'chat' | 'memories' | 'graph' | 'search' | 'dashboard' | 'timeline' | 'journal') => void
  onNewChat: () => void
  onLogout?: () => void
  user?: {
    email: string
    full_name?: string
    avatar_url?: string
  } | null
}

export default function Sidebar({ currentView, onViewChange, onNewChat, onLogout, user }: SidebarProps) {
  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="logo">
          <span className="logo-icon">📚</span>
          <span className="logo-text">Memoir</span>
        </div>
      </div>
      
      <nav className="sidebar-nav">
        <button 
          className={`nav-item ${currentView === 'chat' ? 'active' : ''}`}
          onClick={() => onViewChange('chat')}
        >
          <span className="nav-icon">💬</span>
          <span>Chat</span>
        </button>
        
        <button 
          className={`nav-item ${currentView === 'memories' ? 'active' : ''}`}
          onClick={() => onViewChange('memories')}
        >
          <span className="nav-icon">🧠</span>
          <span>Memories</span>
        </button>

        <button 
          className={`nav-item ${currentView === 'journal' ? 'active' : ''}`}
          onClick={() => onViewChange('journal')}
          title="Journey"
        >
          <span className="nav-icon">📝</span>
          <span>Journal</span>
        </button>

        <button 
          className={`nav-item ${currentView === 'search' ? 'active' : ''}`}
          onClick={() => onViewChange('search')}
        >
          <span className="nav-icon">🔍</span>
          <span>Search</span>
        </button>

        <button 
          className={`nav-item ${currentView === 'graph' ? 'active' : ''}`}
          onClick={() => onViewChange('graph')}
        >
          <span className="nav-icon">🕸️</span>
          <span>Graph</span>
        </button>

        <button 
          className={`nav-item ${currentView === 'dashboard' ? 'active' : ''}`}
          onClick={() => onViewChange('dashboard')}
        >
          <span className="nav-icon">📊</span>
          <span>Dashboard</span>
        </button>

        <button 
          className={`nav-item ${currentView === 'timeline' ? 'active' : ''}`}
          onClick={() => onViewChange('timeline')}
        >
          <span className="nav-icon">📅</span>
          <span>Timeline</span>
        </button>
      </nav>
      
      <div className="sidebar-footer">
        <button className="btn btn-primary new-chat-btn" onClick={onNewChat}>
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
