import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { ChatSessionProvider } from './contexts/ChatSessionContext'
import { DemoProvider } from './contexts/DemoContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { ToastProvider } from './contexts/ToastContext'
import ProtectedRoute from './components/ProtectedRoute'
import ErrorBoundary from './components/ErrorBoundary'
import AppLayout from './components/AppLayout'
import DemoLayout from './components/DemoLayout'
import AuthView from './components/AuthView'
import ChatView from './components/ChatView'
import KakaoLinkPage from './components/KakaoLinkPage'
import LandingPage from './components/LandingPage'
import NotFoundPage from './components/NotFoundPage'
import './App.css'

// 코드 스플리팅: 무거운 뷰를 동적 import로 분리
const MemoryView = lazy(() => import('./components/MemoryView'))
const GraphView = lazy(() => import('./components/GraphView'))
const JournalView = lazy(() => import('./components/JournalView'))
const DashboardView = lazy(() => import('./components/DashboardView'))
const SettingsView = lazy(() => import('./components/SettingsView'))


// '/' 라우트: 비로그인 → 랜딩 페이지, 로그인 → /chat 리다이렉트
function RootRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
      </div>
    )
  }

  return user ? <Navigate to="/chat" replace /> : <LandingPage />
}

function AppRoutes() {
  const location = useLocation()
  return (
    <Routes>
      {/* 공개 라우트 */}
      <Route path="/" element={<RootRoute />} />
      <Route path="/login" element={<AuthView />} />
      <Route path="/kakao-link" element={<KakaoLinkPage />} />

      {/* 데모 모드 — 인증 불필요, API 목 데이터 사용 */}
      <Route path="demo" element={<DemoLayout />}>
        <Route index element={<Navigate to="/demo/dashboard" replace />} />
        <Route path="chat" element={<ChatView key={`demo-chat-${location.key}`} />} />
        <Route path="chat/:sessionId" element={<ChatView key={`demo-chat-${location.key}`} />} />
        <Route path="memories" element={<Suspense fallback={<div className="page-loading" />}><MemoryView key={location.key} /></Suspense>} />
        <Route path="journal" element={<Suspense fallback={<div className="page-loading" />}><JournalView key={location.key} /></Suspense>} />
        <Route path="graph" element={<Suspense fallback={<div className="page-loading" />}><GraphView key={location.key} /></Suspense>} />
        <Route path="dashboard" element={<Suspense fallback={<div className="page-loading" />}><DashboardView key={location.key} /></Suspense>} />
      </Route>

      {/* 인증 필요 라우트 - Sidebar 레이아웃 공유 */}
      <Route
        element={
          <DemoProvider>
            <ProtectedRoute>
              <ChatSessionProvider>
                <AppLayout />
              </ChatSessionProvider>
            </ProtectedRoute>
          </DemoProvider>
        }
      >
        <Route path="chat" element={<ChatView key={`chat-${location.key}`} />} />
        <Route path="chat/:sessionId" element={<ChatView key={`chat-${location.key}`} />} />
        <Route path="memories" element={<Suspense fallback={<div className="page-loading" />}><MemoryView key={location.key} /></Suspense>} />
        <Route path="journal" element={<Suspense fallback={<div className="page-loading" />}><JournalView key={location.key} /></Suspense>} />
        <Route path="graph" element={<Suspense fallback={<div className="page-loading" />}><GraphView key={location.key} /></Suspense>} />
        <Route path="settings" element={<Suspense fallback={<div className="page-loading" />}><SettingsView key={location.key} /></Suspense>} />
        {/* 삭제된 라우트 리다이렉트 */}
        <Route path="search" element={<Navigate to="/memories?tab=search" replace />} />
        <Route path="timeline" element={<Navigate to="/memories?tab=timeline" replace />} />
        <Route path="dashboard" element={<Suspense fallback={<div className="page-loading" />}><DashboardView key={location.key} /></Suspense>} />
        <Route path="*" element={<NotFoundPage />} />
      </Route>

      {/* 매칭되지 않는 모든 경로 → 404 */}
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  )
}

function App() {
  return (
    <ErrorBoundary>
    <BrowserRouter>
      <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <AppRoutes />
        </ToastProvider>
      </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
