import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'
import './AuthView.css'

export default function AuthView() {
  const { user, isLoading, signIn, signUp, signInWithGoogle, signInAsDev } = useAuth()
  const location = useLocation()
  const isDev = import.meta.env.DEV

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

  const handleGoogleLogin = async () => {
    setError('')
    try {
      await signInWithGoogle()
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
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

        {/* OAuth buttons */}
        {supabase && (
          <div className="oauth-section">
            <button
              type="button"
              className="btn oauth-btn google-btn"
              onClick={handleGoogleLogin}
              disabled={isSubmitting}
            >
              <svg viewBox="0 0 24 24" width="18" height="18">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              Google로 로그인
            </button>

            <div className="auth-divider">
              <span>또는</span>
            </div>
          </div>
        )}

        {/* Email/password form */}
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

        {/* Dev mode bypass */}
        {isDev && (
          <div className="dev-section">
            <button
              type="button"
              className="btn dev-login-btn"
              onClick={signInAsDev}
            >
              Dev Login (로그인 없이 진입)
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
