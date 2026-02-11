import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { useAuth } from '../contexts/AuthContext'
import '../App.css'

// 인증된 라우트의 공통 레이아웃 (사이드바 + 메인 콘텐츠)
export default function AppLayout() {
  const { signOut, user } = useAuth()

  return (
    <div className="app-container">
      <Sidebar onLogout={signOut} user={user} />
      <main className="main-content">
        <Outlet />
      </main>
    </div>
  )
}
