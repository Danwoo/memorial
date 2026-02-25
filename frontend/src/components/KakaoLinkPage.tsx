import { useState, useEffect } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { supabase } from '../lib/supabase'
import { completeKakaoLinkByToken } from '../api'
import './AuthView.css'

type LinkStatus = 'loading' | 'linking' | 'success' | 'error' | 'login-required' | 'redirecting'

// 카카오톡 인앱 브라우저 감지
function isKakaoTalkInAppBrowser(): boolean {
  return /KAKAOTALK/i.test(navigator.userAgent)
}

export default function KakaoLinkPage() {
  const { user, isLoading } = useAuth()
  const [searchParams] = useSearchParams()
  const navigate = useNavigate()

  const tokenFromUrl = searchParams.get('token')
  const [status, setStatus] = useState<LinkStatus>('loading')
  const [errorMsg, setErrorMsg] = useState('')
  const [loginPending, setLoginPending] = useState(false)

  // 카카오톡 인앱 브라우저 → 외부 브라우저로 강제 전환
  // OAuth 로그인이 인앱 브라우저에서 정상 동작하지 않으므로 외부 브라우저 필요
  useEffect(() => {
    if (!isKakaoTalkInAppBrowser()) return
    setStatus('redirecting')
    const currentUrl = window.location.href
    // 카카오톡 인앱 브라우저에서 외부 브라우저로 열기
    window.location.href = `kakaotalk://web/openExternal?url=${encodeURIComponent(currentUrl)}`
  }, [])

  // URL 토큰을 sessionStorage에 보관 (OAuth 리다이렉트 후에도 유지)
  useEffect(() => {
    if (tokenFromUrl) {
      sessionStorage.setItem('kakao_link_token', tokenFromUrl)
    }
  }, [tokenFromUrl])

  const token = tokenFromUrl || sessionStorage.getItem('kakao_link_token')

  useEffect(() => {
    if (isLoading) return

    if (!token) {
      setStatus('error')
      setErrorMsg('연결 토큰이 없습니다. 카카오톡에서 Memoir 채널에 메시지를 보내 새 링크를 받아주세요.')
      return
    }

    if (!user) {
      setStatus('login-required')
      return
    }

    // 로그인 완료 — API 호출로 채널 연결
    setStatus('linking')
    completeKakaoLinkByToken(token)
      .then(() => {
        sessionStorage.removeItem('kakao_link_token')
        setStatus('success')
      })
      .catch((err: unknown) => {
        const raw = err instanceof Error ? err.message : ''
        let detail = '연결에 실패했습니다.'
        if (raw.includes('만료') || raw.includes('expired')) {
          detail = '링크가 만료되었습니다. 카카오톡에서 Memoir 채널에 메시지를 보내 새 링크를 받아주세요.'
        } else if (raw) {
          detail = raw
        }
        setStatus('error')
        setErrorMsg(detail)
      })
  }, [user, isLoading, token])

  const handleOAuthLogin = async (provider: 'google' | 'kakao') => {
    if (!supabase) return
    setLoginPending(true)
    // OAuth redirect URL에 토큰을 포함 — 카카오톡 인앱 브라우저에서
    // 외부 브라우저로 전환 시 sessionStorage가 유실되므로 URL로 전달
    const redirectUrl = token
      ? `${window.location.origin}/kakao-link?token=${encodeURIComponent(token)}`
      : `${window.location.origin}/kakao-link`
    const options: { redirectTo: string; scopes?: string } = {
      redirectTo: redirectUrl,
    }
    if (provider === 'kakao') {
      options.scopes = 'account_email profile_nickname talk_message'
    }
    await supabase.auth.signInWithOAuth({ provider, options })
  }

  return (
    <div className="auth-view">
      <div className="auth-container">
        <div className="auth-header">
          <img src="/favicon.png" alt="Memoir" width={64} height={64} className="auth-logo" />
          <h1>Memoir AI</h1>
          <p>카카오톡 채널 연결</p>
        </div>

        {status === 'redirecting' && (
          <div style={{ textAlign: 'center', padding: '2rem 0' }}>
            <div className="loading-spinner" />
            <p style={{ color: 'var(--text-secondary)', marginTop: '1rem' }}>
              외부 브라우저로 이동 중...
            </p>
            <p style={{ color: 'var(--text-tertiary, #999)', fontSize: '0.8rem', marginTop: '0.5rem' }}>
              자동으로 이동하지 않으면{' '}
              <a href={window.location.href} target="_blank" rel="noopener noreferrer">
                여기를 눌러주세요
              </a>
            </p>
          </div>
        )}

        {status === 'loading' && (
          <div style={{ textAlign: 'center', padding: '2rem 0' }}>
            <div className="loading-spinner" />
          </div>
        )}

        {status === 'login-required' && (
          <>
            <p style={{ textAlign: 'center', color: 'var(--text-secondary)', marginBottom: '1.5rem' }}>
              채널 연결을 위해 먼저 로그인해주세요.
            </p>
            <div className="oauth-section">
              <button
                type="button"
                className="btn oauth-btn google-btn"
                onClick={() => handleOAuthLogin('google')}
                disabled={loginPending}
              >
                <svg viewBox="0 0 24 24" width="18" height="18">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                Continue with Google
              </button>

              <button
                type="button"
                className="btn oauth-btn kakao-btn"
                onClick={() => handleOAuthLogin('kakao')}
                disabled={loginPending}
              >
                <svg viewBox="0 0 24 24" width="18" height="18" fill="#3c1e1e">
                  <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
                </svg>
                Continue with Kakao
              </button>
            </div>
          </>
        )}

        {status === 'linking' && (
          <div style={{ textAlign: 'center', padding: '2rem 0' }}>
            <div className="loading-spinner" />
            <p style={{ color: 'var(--text-secondary)', marginTop: '1rem' }}>채널 연결 중...</p>
          </div>
        )}

        {status === 'success' && (
          <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              background: 'var(--color-success, #22c55e)', color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '1.5rem', fontWeight: 700, margin: '0 auto 1rem',
            }}>
              ✓
            </div>
            <p style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.5rem' }}>
              카카오톡 채널이 연결되었습니다!
            </p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
              이제 카카오톡에서 URL이나 텍스트를 보내면<br />Memoir에 자동 저장됩니다.
            </p>
            <button
              className="btn btn-primary"
              onClick={() => navigate('/dashboard')}
              style={{ width: '100%' }}
            >
              Memoir 시작하기
            </button>
          </div>
        )}

        {status === 'error' && (
          <div style={{ textAlign: 'center', padding: '1.5rem 0' }}>
            <div style={{
              width: 56, height: 56, borderRadius: '50%',
              background: 'var(--color-error, #ef4444)', color: '#fff',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '1.5rem', fontWeight: 700, margin: '0 auto 1rem',
            }}>
              ✕
            </div>
            <p style={{ fontSize: '1.1rem', fontWeight: 600, marginBottom: '0.5rem' }}>
              연결에 실패했습니다
            </p>
            <p style={{ color: 'var(--text-secondary)', fontSize: '0.9rem', marginBottom: '1.5rem' }}>
              {errorMsg}
            </p>
            <a
              href="https://pf.kakao.com/_NxoGzX/chat"
              target="_blank"
              rel="noopener noreferrer"
              className="btn btn-primary"
              style={{ width: '100%', textAlign: 'center', textDecoration: 'none', display: 'block' }}
            >
              카카오톡에서 새 링크 받기
            </a>
          </div>
        )}
      </div>
    </div>
  )
}
