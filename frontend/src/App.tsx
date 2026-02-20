import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
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
import './App.css'

// 코드 스플리팅: 무거운 뷰를 동적 import로 분리
const MemoryView = lazy(() => import('./components/MemoryView'))
const GraphView = lazy(() => import('./components/GraphView'))
const JournalView = lazy(() => import('./components/JournalView'))
const DashboardView = lazy(() => import('./components/DashboardView'))
const SettingsView = lazy(() => import('./components/SettingsView'))

// 데모 뷰 (코드 스플리팅)
const DemoChatView = lazy(() => import('./components/demo/DemoChatView'))
const DemoMemoryView = lazy(() => import('./components/demo/DemoMemoryView'))
const DemoJournalView = lazy(() => import('./components/demo/DemoJournalView'))
const DemoGraphView = lazy(() => import('./components/demo/DemoGraphView'))
const DemoDashboardView = lazy(() => import('./components/demo/DemoDashboardView'))

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

function App() {
  return (
    <ErrorBoundary>
    <BrowserRouter>
      <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            {/* 공개 라우트 */}
            <Route path="/" element={<RootRoute />} />
            <Route path="/login" element={<AuthView />} />
            <Route path="/kakao-link" element={<KakaoLinkPage />} />

            {/* 데모 모드 — 인증 불필요, 읽기 전용 */}
            <Route path="demo" element={<DemoLayout />}>
              <Route index element={<Navigate to="/demo/dashboard" replace />} />
              <Route path="chat" element={<Suspense fallback={<div className="page-loading" />}><DemoChatView /></Suspense>} />
              <Route path="chat/:sessionId" element={<Suspense fallback={<div className="page-loading" />}><DemoChatView /></Suspense>} />
              <Route path="memories" element={<Suspense fallback={<div className="page-loading" />}><DemoMemoryView /></Suspense>} />
              <Route path="journal" element={<Suspense fallback={<div className="page-loading" />}><DemoJournalView /></Suspense>} />
              <Route path="graph" element={<Suspense fallback={<div className="page-loading" />}><DemoGraphView /></Suspense>} />
              <Route path="dashboard" element={<Suspense fallback={<div className="page-loading" />}><DemoDashboardView /></Suspense>} />
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
              <Route path="chat" element={<ChatView />} />
              <Route path="chat/:sessionId" element={<ChatView />} />
              <Route path="memories" element={<Suspense fallback={<div className="page-loading" />}><MemoryView /></Suspense>} />
              <Route path="journal" element={<Suspense fallback={<div className="page-loading" />}><JournalView /></Suspense>} />
              <Route path="graph" element={<Suspense fallback={<div className="page-loading" />}><GraphView /></Suspense>} />
              <Route path="settings" element={<Suspense fallback={<div className="page-loading" />}><SettingsView /></Suspense>} />
              {/* 삭제된 라우트 리다이렉트 */}
              <Route path="search" element={<Navigate to="/memories?tab=search" replace />} />
              <Route path="timeline" element={<Navigate to="/memories?tab=timeline" replace />} />
              <Route path="dashboard" element={<Suspense fallback={<div className="page-loading" />}><DashboardView /></Suspense>} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
    </ErrorBoundary>
  )
}

export default App
