import { useState, useCallback, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu } from 'lucide-react'
import Sidebar from './Sidebar'
import CommandPalette from './CommandPalette'
import { useAuth } from '../contexts/AuthContext'
import '../App.css'

// 인증된 라우트의 공통 레이아웃 (사이드바 + 메인 콘텐츠)
export default function AppLayout() {
  const { signOut, user } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [showCmdPalette, setShowCmdPalette] = useState(false)

  const closeMobile = useCallback(() => setMobileOpen(false), [])

  // Cmd+K / Ctrl+K 글로벌 단축키
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowCmdPalette((v) => !v)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  return (
    <div className="app-container">
      <a href="#main-content" className="skip-link">본문으로 건너뛰기</a>
      <button
        className="mobile-nav-toggle"
        onClick={() => setMobileOpen(true)}
        type="button"
        aria-label="메뉴 열기"
      >
        <Menu size={22} />
      </button>
      <Sidebar onLogout={signOut} user={user} mobileOpen={mobileOpen} onMobileClose={closeMobile} />
      <main className="main-content" id="main-content">
        <Outlet />
      </main>
      <CommandPalette isOpen={showCmdPalette} onClose={() => setShowCmdPalette(false)} />
    </div>
  )
}
