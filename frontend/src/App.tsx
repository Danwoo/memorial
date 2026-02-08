import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import AppLayout from './components/AppLayout'
import AuthView from './components/AuthView'
import ChatView from './components/ChatView'
import MemoryView from './components/MemoryView'
import GraphView from './components/GraphView'
import JournalView from './components/JournalView'
import SearchView from './components/SearchView'
import DashboardView from './components/DashboardView'
import TimelineView from './components/TimelineView'
import './App.css'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public route */}
          <Route path="/login" element={<AuthView />} />

          {/* Protected routes share the Sidebar layout */}
          <Route
            element={
              <ProtectedRoute>
                <AppLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<DashboardView />} />
            <Route path="chat" element={<ChatView />} />
            <Route path="memories" element={<MemoryView />} />
            <Route path="journal" element={<JournalView />} />
            <Route path="search" element={<SearchView />} />
            <Route path="graph" element={<GraphView />} />
            <Route path="timeline" element={<TimelineView />} />
          </Route>
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
