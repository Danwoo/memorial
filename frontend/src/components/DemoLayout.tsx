import { Outlet, useNavigate } from 'react-router-dom'
import { useState, useMemo, useEffect } from 'react'
import { Sparkles } from 'lucide-react'
import { DemoProvider, DEMO_USER } from '../contexts/DemoContext'
import { AuthContext } from '../contexts/AuthContext'
import { SocratesSessionProvider } from '../contexts/SocratesSessionContext'
import { useIsMobile } from '../hooks/useMediaQuery'
import Sidebar from './Sidebar'
import MobileTabBar from './MobileTabBar'
import CommandPalette from './CommandPalette'
import '../App.css'
import './DemoLayout.css'

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const noop = async (..._args: any[]) => {}

export default function DemoLayout() {
  const navigate = useNavigate()
  const isMobile = useIsMobile()
  const [showCmdPalette, setShowCmdPalette] = useState(false)

  // Ctrl+K / Cmd+K 글로벌 단축키 (데모 모드)
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

  const demoAuthValue = useMemo(() => ({
    user: DEMO_USER as import('../types').User,
    session: null,
    isLoading: false,
    signInWithGoogle: noop,
    signInWithKakao: noop,
    signOut: noop,
    linkProvider: noop as (provider: 'google' | 'kakao') => Promise<void>,
    unlinkProvider: noop as (identity: import('@supabase/supabase-js').UserIdentity) => Promise<void>,
  }), [])

  return (
    <DemoProvider demo>
      <AuthContext.Provider value={demoAuthValue}>
        <SocratesSessionProvider>
          <div className="demo-banner">
            <Sparkles size={14} />
            <span>데모 모드 — 샘플 데이터로 체험 중</span>
            <button className="demo-banner-cta" onClick={() => navigate('/login')} type="button">
              회원가입하고 시작하기
            </button>
          </div>
          <div className={`app-container demo-app-container ${isMobile ? 'app-container--mobile' : ''}`}>
            {!isMobile && <Sidebar user={DEMO_USER} />}
            <main className="main-content" id="main-content">
              <Outlet />
            </main>
            {isMobile && <MobileTabBar user={DEMO_USER} prefix="/demo" />}
            <CommandPalette isOpen={showCmdPalette} onClose={() => setShowCmdPalette(false)} />
          </div>
        </SocratesSessionProvider>
      </AuthContext.Provider>
    </DemoProvider>
  )
}
