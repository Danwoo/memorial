import { useState, useCallback, useEffect } from 'react'
import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import MobileTabBar from './MobileTabBar'
import CommandPalette from './CommandPalette'
import OnboardingWizard from './OnboardingWizard'
import { useAuth } from '../contexts/AuthContext'
import { useMediaQuery } from '../hooks/useMediaQuery'
import '../App.css'

const ONBOARDING_KEY = 'onboarding_completed'

// 인증된 라우트의 공통 레이아웃 (사이드바 + 메인 콘텐츠)
export default function AppLayout() {
  const { signOut, user } = useAuth()
  const isMobile = useMediaQuery('(max-width: 767px)')
  const [showCmdPalette, setShowCmdPalette] = useState(false)
  const [showOnboarding, setShowOnboarding] = useState(
    () => !localStorage.getItem(ONBOARDING_KEY),
  )

  const handleOnboardingComplete = useCallback(() => {
    localStorage.setItem(ONBOARDING_KEY, 'true')
    setShowOnboarding(false)
  }, [])

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
    <div className={`app-container ${isMobile ? 'app-container--mobile' : ''}`}>
      <a href="#main-content" className="skip-link">본문으로 건너뛰기</a>
      {!isMobile && (
        <Sidebar onLogout={signOut} user={user} />
      )}
      <main className="main-content" id="main-content">
        <Outlet />
      </main>
      {isMobile && <MobileTabBar user={user} onLogout={signOut} />}
      <CommandPalette isOpen={showCmdPalette} onClose={() => setShowCmdPalette(false)} />
      {showOnboarding && <OnboardingWizard onComplete={handleOnboardingComplete} />}
    </div>
  )
}
