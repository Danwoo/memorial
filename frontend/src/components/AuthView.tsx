import { useState } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import './AuthView.css'

export default function AuthView() {
  const { user, isLoading, signInWithGoogle, signInWithKakao } = useAuth()
  const location = useLocation()

  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Redirect if already authenticated
  const redirectTo = (location.state as { from?: string })?.from ?? '/'
  if (!isLoading && user) {
    return <Navigate to={redirectTo} replace />
  }

  const handleOAuthLogin = async (provider: 'google' | 'kakao') => {
    setError('')
    setIsSubmitting(true)
    try {
      if (provider === 'google') {
        await signInWithGoogle()
      } else {
        await signInWithKakao()
      }
    } catch (err) {
      if (err instanceof Error) {
        setError(err.message)
      }
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

        <div className="oauth-section">
          <button
            type="button"
            className="btn oauth-btn google-btn"
            onClick={() => handleOAuthLogin('google')}
            disabled={isSubmitting}
          >
            <svg viewBox="0 0 24 24" width="18" height="18">
              <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
              <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
              <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
              <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
            </svg>
            Google로 시작하기
          </button>

          <button
            type="button"
            className="btn oauth-btn kakao-btn"
            onClick={() => handleOAuthLogin('kakao')}
            disabled={isSubmitting}
          >
            <svg viewBox="0 0 24 24" width="18" height="18" fill="#3c1e1e">
              <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
            </svg>
            카카오로 시작하기
          </button>
        </div>

        {error && <div className="auth-error">{error}</div>}
      </div>
    </div>
  )
}
