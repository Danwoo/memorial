import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import { ThemeProvider } from './contexts/ThemeContext'
import { ToastProvider } from './contexts/ToastContext'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/AppLayout'
import AuthView from './components/AuthView'
import ChatView from './components/ChatView'
import MemoryView from './components/MemoryView'
import GraphView from './components/GraphView'
import JournalView from './components/JournalView'
import SettingsView from './components/SettingsView'
import './App.css'

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
              <Route path="memories" element={<MemoryView />} />
              <Route path="journal" element={<JournalView />} />
              <Route path="graph" element={<GraphView />} />
              <Route path="settings" element={<SettingsView />} />
              {/* 삭제된 라우트 리다이렉트 */}
              <Route path="search" element={<Navigate to="/memories?tab=search" replace />} />
              <Route path="timeline" element={<Navigate to="/memories?tab=timeline" replace />} />
              <Route path="dashboard" element={<Navigate to="/chat" replace />} />
            </Route>
          </Routes>
        </ToastProvider>
      </AuthProvider>
      </ThemeProvider>
    </BrowserRouter>
  )
}

export default App
