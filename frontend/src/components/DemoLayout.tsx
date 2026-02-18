import { Outlet, useNavigate } from 'react-router-dom'
import { useState, useCallback } from 'react'
import { Menu, Sparkles } from 'lucide-react'
import { DemoProvider } from '../contexts/DemoContext'
import DemoSidebar from './DemoSidebar'
import CommandPalette from './CommandPalette'
import '../App.css'
import './DemoLayout.css'

export default function DemoLayout() {
  const navigate = useNavigate()
  const [mobileOpen, setMobileOpen] = useState(false)
  const [showCmdPalette, setShowCmdPalette] = useState(false)

  const closeMobile = useCallback(() => setMobileOpen(false), [])

  return (
    <DemoProvider demo>
      <div className="demo-banner">
        <Sparkles size={14} />
        <span>데모 모드 — 샘플 데이터로 체험 중</span>
        <button className="demo-banner-cta" onClick={() => navigate('/login')} type="button">
          회원가입하고 시작하기
        </button>
      </div>
      <div className="app-container demo-app-container">
        <button
          className="mobile-nav-toggle"
          onClick={() => setMobileOpen(true)}
          type="button"
          aria-label="메뉴 열기"
        >
          <Menu size={22} />
        </button>
        <DemoSidebar mobileOpen={mobileOpen} onMobileClose={closeMobile} />
        <main className="main-content" id="main-content">
          <Outlet />
        </main>
        <CommandPalette isOpen={showCmdPalette} onClose={() => setShowCmdPalette(false)} />
      </div>
    </DemoProvider>
  )
}
