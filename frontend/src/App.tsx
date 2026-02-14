import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { ToastProvider } from './contexts/ToastContext'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/AppLayout'
import AuthView from './components/AuthView'
import ChatView from './components/ChatView'
import './App.css'

// 코드 스플리팅: 무거운 뷰를 동적 import로 분리
const MemoryView = lazy(() => import('./components/MemoryView'))
const GraphView = lazy(() => import('./components/GraphView'))
const JournalView = lazy(() => import('./components/JournalView'))
const DashboardView = lazy(() => import('./components/DashboardView'))
const SettingsView = lazy(() => import('./components/SettingsView'))

function App() {
  return (
    <BrowserRouter>
      <ThemeProvider>
      <AuthProvider>
        <ToastProvider>
          <Routes>
            {/* 비인증 공개 라우트 */}
            <Route path="/login" element={<AuthView />} />

            {/* 인증 필요 라우트 - Sidebar 레이아웃 공유 */}
            <Route
              element={
                <ProtectedRoute>
                  <AppLayout />
                </ProtectedRoute>
              }
            >
              <Route index element={<ChatView />} />
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
  )
}

export default App
