import { useState, useEffect } from 'react'
import './App.css'
import Sidebar from './components/Sidebar'
import ChatView from './components/ChatView'
import MemoryView from './components/MemoryView'
import GraphView from './components/GraphView'
import JournalView from './components/JournalView'
import SearchView from './components/SearchView'
import DashboardView from './components/DashboardView'
import TimelineView from './components/TimelineView'
import AuthView from './components/AuthView'
import type { View, User } from './types'

function App() {
  const [currentView, setCurrentView] = useState<View>('chat')
  const [sessionId, setSessionId] = useState<string | null>(null)
  // In development mode, bypass auth with a dev user.
  // In production, require real authentication.
  const isDev = import.meta.env.DEV
  const [isAuthenticated, setIsAuthenticated] = useState(isDev)
  const [user, setUser] = useState<User | null>(
    isDev
      ? { id: "dev-user", email: "dev@example.com", full_name: "Developer", avatar_url: "" }
      : null
  )
  const [isLoading, setIsLoading] = useState(!isDev)

  // Check for existing auth token on mount (production only)
  useEffect(() => {
    if (isDev) return

    const token = localStorage.getItem('auth_token')
    if (token) {
      fetch('/api/v1/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
        .then(res => {
          if (res.ok) {
            return res.json()
          }
          throw new Error('Invalid token')
        })
        .then(data => {
          setUser(data)
          setIsAuthenticated(true)
        })
        .catch(() => {
          localStorage.removeItem('auth_token')
        })
        .finally(() => setIsLoading(false))
    } else {
      setIsLoading(false)
    }
  }, [isDev])

  const handleLogin = (_token: string, userData: User) => {
    setUser(userData)
    setIsAuthenticated(true)
  }

  const handleLogout = () => {
    localStorage.removeItem('auth_token')
    setUser(null)
    setIsAuthenticated(false)
  }

  // Show loading state
  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
        <p>Loading...</p>
      </div>
    )
  }

  // Show auth view if not authenticated
  if (!isAuthenticated) {
    return <AuthView onLogin={handleLogin} />
  }

  return (
    <div className="app-container">
      <Sidebar 
        currentView={currentView} 
        onViewChange={setCurrentView}
        onNewChat={() => setSessionId(null)}
        onLogout={handleLogout}
        user={user}
      />
      <main className="main-content">
        {currentView === 'chat' && (
          <ChatView 
            sessionId={sessionId}
            onSessionCreate={setSessionId}
          />
        )}
        {currentView === 'memories' && <MemoryView />}
        {currentView === 'journal' && <JournalView />}
        {currentView === 'graph' && <GraphView />}
        {currentView === 'search' && <SearchView />}
        {currentView === 'dashboard' && <DashboardView />}
        {currentView === 'timeline' && <TimelineView />}
      </main>
    </div>
  )
}

export default App
