import { useEffect, useState } from 'react'
import { X } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './AuthModal.css'

interface AuthModalProps {
  open: boolean
  onClose: () => void
}

export default function AuthModal({ open, onClose }: AuthModalProps) {
  const { signInWithGoogle, signInWithKakao } = useAuth()
  const [submitting, setSubmitting] = useState<'google' | 'kakao' | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open) return null

  const handleOAuth = async (provider: 'google' | 'kakao') => {
    if (submitting) return
    setError('')
    setSubmitting(provider)
    try {
      if (provider === 'google') {
        await signInWithGoogle()
      } else {
        await signInWithKakao()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '로그인 중 오류가 발생했어요')
      setSubmitting(null)
    }
  }

  return (
    <div className="auth-modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="auth-modal-title">
      <div className="auth-modal" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          className="auth-modal-close"
          onClick={onClose}
          aria-label="닫기"
        >
          <X size={18} />
        </button>

        <div className="auth-modal-logo">
          <img src="/logos/logo-final.svg" width={48} height={48} alt="Memoir" />
        </div>

        <h2 id="auth-modal-title" className="auth-modal-title">Memoir 시작하기</h2>
        <p className="auth-modal-subtitle">30초면 충분해요. 카카오 또는 구글 계정으로 시작하세요.</p>

        <div className="auth-modal-buttons">
          <button
            type="button"
            className="auth-oauth-btn auth-oauth-kakao"
            onClick={() => handleOAuth('kakao')}
            disabled={submitting !== null}
          >
            {submitting === 'kakao' ? (
              <span className="auth-oauth-spinner auth-oauth-spinner-dark" aria-hidden="true" />
            ) : (
              <svg viewBox="0 0 24 24" width="18" height="18" fill="#3c1e1e" aria-hidden="true">
                <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
              </svg>
            )}
            카카오로 시작하기
          </button>

          <button
            type="button"
            className="auth-oauth-btn auth-oauth-google"
            onClick={() => handleOAuth('google')}
            disabled={submitting !== null}
          >
            {submitting === 'google' ? (
              <span className="auth-oauth-spinner" aria-hidden="true" />
            ) : (
              <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
            )}
            Google로 시작하기
          </button>
        </div>

        {error && <div className="auth-modal-error">{error}</div>}

        <p className="auth-modal-terms">
          계속 진행하면 Memoir의 <a href="#">이용약관</a>과{' '}
          <a href="#">개인정보처리방침</a>에 동의하는 것으로 간주돼요.
        </p>
      </div>
    </div>
  )
}
