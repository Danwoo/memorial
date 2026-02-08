import { Outlet } from 'react-router-dom'
import Sidebar from './Sidebar'
import { useAuth } from '../contexts/AuthContext'
import '../App.css'

/**
 * Persistent layout for authenticated routes.
 * Renders the Sidebar alongside the main content area.
 * Child routes are rendered via <Outlet />.
 */
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
