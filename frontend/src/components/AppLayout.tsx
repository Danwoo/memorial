import { useState, useEffect, useCallback } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import MobileTabBar from './MobileTabBar'
import CommandPalette from './CommandPalette'
import ShortcutsModal from './ShortcutsModal'
import { useAuth } from '../contexts/AuthContext'
import { useIsMobile } from '../hooks/useMediaQuery'
import '../App.css'

const ONBOARDING_KEY = 'memoir:onboarded'

// 인증된 라우트의 공통 레이아웃 (사이드바 + 메인 콘텐츠)
export default function AppLayout() {
  const { signOut, user } = useAuth()
  const isMobile = useIsMobile()
  const [showCmdPalette, setShowCmdPalette] = useState(false)
  const [showShortcuts, setShowShortcuts] = useState(false)

  // Cmd+K / Ctrl+K + ? 글로벌 단축키
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault()
        setShowCmdPalette((v) => !v)
      } else if (e.key === '?' && !e.ctrlKey && !e.metaKey && !(e.target instanceof HTMLInputElement) && !(e.target instanceof HTMLTextAreaElement)) {
        setShowShortcuts((v) => !v)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [])

  const handleOpenHelp = useCallback(() => {
    localStorage.removeItem(ONBOARDING_KEY)
    window.dispatchEvent(new CustomEvent('memoir:show-onboarding'))
  }, [])

  return (
    <div className={`app-container ${isMobile ? 'app-container--mobile' : ''}`}>
      <a href="#main-content" className="skip-link">본문으로 건너뛰기</a>
      {!isMobile && (
        <Sidebar onLogout={signOut} user={user} onOpenHelp={handleOpenHelp} />
      )}
      <main className="main-content" id="main-content">
        <Outlet />
      </main>
      {isMobile && <MobileTabBar user={user} onLogout={signOut} onOpenSearch={() => setShowCmdPalette(true)} />}
      <CommandPalette isOpen={showCmdPalette} onClose={() => setShowCmdPalette(false)} />
      {showShortcuts && <ShortcutsModal onClose={() => setShowShortcuts(false)} />}
    </div>
  )
}
