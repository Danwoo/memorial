import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import './AuthView.css'

/**
 * Login / Signup view.
 * Redirects authenticated users to the page they originally requested,
 * or to the dashboard by default.
 */
export default function AuthView() {
  const { user, isLoading, signIn, signUp } = useAuth()
  const location = useLocation()

  const [isLogin, setIsLogin] = useState(true)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Redirect if already authenticated
  const redirectTo = (location.state as { from?: string })?.from ?? '/'
  if (!isLoading && user) {
    return <Navigate to={redirectTo} replace />
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      if (isLogin) {
        await signIn(email, password)
      } else {
        await signUp(email, password)
      }
      // After successful auth, the Navigate above will handle redirection
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message || 'Authentication failed')
      } else {
        setError('Network error. Please try again.')
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="auth-view">
      <div className="auth-container glass-card">
        <div className="auth-header">
          <span className="auth-logo">📚</span>
          <h1>Memoir AI</h1>
          <p>지능형 인지 장부</p>
        </div>

        <div className="auth-tabs">
          <button
            className={`auth-tab ${isLogin ? 'active' : ''}`}
            onClick={() => setIsLogin(true)}
          >
            로그인
          </button>
          <button
            className={`auth-tab ${!isLogin ? 'active' : ''}`}
            onClick={() => setIsLogin(false)}
          >
            회원가입
          </button>
        </div>

        <form onSubmit={handleSubmit} className="auth-form">
          <div className="input-group">
            <label htmlFor="email">이메일</label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              required
            />
          </div>

          <div className="input-group">
            <label htmlFor="password">비밀번호</label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••"
              required
              minLength={6}
            />
          </div>

          {error && <div className="auth-error">{error}</div>}

          <button
            type="submit"
            className="btn btn-primary auth-submit"
            disabled={isSubmitting}
          >
            {isSubmitting ? '처리 중...' : isLogin ? '로그인' : '가입하기'}
          </button>
        </form>
      </div>
    </div>
  )
}
