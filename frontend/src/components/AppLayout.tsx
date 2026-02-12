import { useState, useCallback } from 'react'
import { Outlet } from 'react-router-dom'
import { Menu } from 'lucide-react'
import Sidebar from './Sidebar'
import { useAuth } from '../contexts/AuthContext'
import '../App.css'

// 인증된 라우트의 공통 레이아웃 (사이드바 + 메인 콘텐츠)
export default function AppLayout() {
  const { signOut, user } = useAuth()
  const [mobileOpen, setMobileOpen] = useState(false)

  const closeMobile = useCallback(() => setMobileOpen(false), [])

  return (
    <div className="app-container">
      <button
        className="mobile-nav-toggle"
        onClick={() => setMobileOpen(true)}
        type="button"
        aria-label="메뉴 열기"
      >
        <Menu size={22} />
      </button>
      <Sidebar onLogout={signOut} user={user} mobileOpen={mobileOpen} onMobileClose={closeMobile} />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
