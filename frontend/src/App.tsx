import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { AuthProvider, useAuth } from './contexts/AuthContext'
import { SocratesSessionProvider } from './contexts/SocratesSessionContext'
import { DemoProvider } from './contexts/DemoContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { ToastProvider } from './contexts/ToastContext'
import ProtectedRoute from './components/ProtectedRoute'
import ErrorBoundary from './components/ErrorBoundary'
import AppLayout from './components/AppLayout'
import DemoLayout from './components/DemoLayout'
// SocratesView는 더 이상 독립 라우트로 사용하지 않음 (다이어리/스크랩에 통합)
import KakaoLinkPage from './components/KakaoLinkPage'
import LandingPage from './components/LandingPage'
import NotFoundPage from './components/NotFoundPage'
import './App.css'

// 코드 스플리팅: 무거운 뷰를 동적 import로 분리
const ScrapView = lazy(() => import('./components/ScrapView'))
const MindmapView = lazy(() => import('./components/MindmapView'))
const DiaryView = lazy(() => import('./components/DiaryView'))
const CalendarView = lazy(() => import('./components/CalendarView'))
const SettingsView = lazy(() => import('./components/SettingsView'))


// '/' 라우트: 비로그인 → 랜딩 페이지, 로그인 → /calendar 리다이렉트
function RootRoute() {
  const { user, isLoading } = useAuth()

  if (isLoading) {
    return (
      <div className="app-loading">
        <div className="loading-spinner"></div>
      </div>
    )
  }

  return user ? <Navigate to="/calendar" replace /> : <LandingPage />
}

function AppRoutes() {
  const location = useLocation()
  return (
    <Routes>
      {/* 공개 라우트 */}
      <Route path="/" element={<RootRoute />} />
      <Route path="/login" element={<Navigate to="/" replace />} />
      <Route path="/kakao-link" element={<KakaoLinkPage />} />

      {/* 데모 모드 — 인증 불필요, API 목 데이터 사용 */}
      <Route path="demo" element={<DemoLayout />}>
        <Route index element={<Navigate to="/demo/calendar" replace />} />
        <Route path="calendar" element={<Suspense fallback={<div className="page-loading" />}><CalendarView key={location.key} /></Suspense>} />
        <Route path="diary" element={<Suspense fallback={<div className="page-loading" />}><DiaryView key={location.key} /></Suspense>} />
        <Route path="scraps" element={<Suspense fallback={<div className="page-loading" />}><ScrapView key={location.key} /></Suspense>} />
        <Route path="mindmap" element={<Suspense fallback={<div className="page-loading" />}><MindmapView key={location.key} /></Suspense>} />
        <Route path="chat" element={<Navigate to="/demo/diary" replace />} />
        <Route path="chat/:sessionId" element={<Navigate to="/demo/diary" replace />} />
        {/* 이전 경로 리다이렉트 */}
        <Route path="dashboard" element={<Navigate to="/demo/calendar" replace />} />
        <Route path="journal" element={<Navigate to="/demo/diary" replace />} />
        <Route path="memories" element={<Navigate to="/demo/scraps" replace />} />
        <Route path="graph" element={<Navigate to="/demo/mindmap" replace />} />
      </Route>

      {/* 인증 필요 라우트 - Sidebar 레이아웃 공유 */}
      <Route
        element={
          <DemoProvider>
            <ProtectedRoute>
              <SocratesSessionProvider>
                <AppLayout />
              </SocratesSessionProvider>
            </ProtectedRoute>
          </DemoProvider>
        }
      >
        <Route path="calendar" element={<Suspense fallback={<div className="page-loading" />}><CalendarView key={location.key} /></Suspense>} />
        <Route path="diary" element={<Suspense fallback={<div className="page-loading" />}><DiaryView key={location.key} /></Suspense>} />
        <Route path="scraps" element={<Suspense fallback={<div className="page-loading" />}><ScrapView key={location.key} /></Suspense>} />
        <Route path="mindmap" element={<Suspense fallback={<div className="page-loading" />}><MindmapView key={location.key} /></Suspense>} />
        <Route path="settings" element={<Suspense fallback={<div className="page-loading" />}><SettingsView key={location.key} /></Suspense>} />
        {/* 삭제/이동된 라우트 리다이렉트 */}
        <Route path="chat" element={<Navigate to="/diary" replace />} />
        <Route path="chat/:sessionId" element={<Navigate to="/diary" replace />} />
        <Route path="search" element={<Navigate to="/scraps?tab=search" replace />} />
        <Route path="timeline" element={<Navigate to="/scraps?tab=timeline" replace />} />
        {/* 이전 경로 리다이렉트 */}
        <Route path="dashboard" element={<Navigate to="/calendar" replace />} />
        <Route path="journal" element={<Navigate to="/diary" replace />} />
        <Route path="memories" element={<Navigate to="/scraps" replace />} />
        <Route path="graph" element={<Navigate to="/mindmap" replace />} />
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
