import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { BookOpen, MessageCircle, PenTool, Network } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import './LandingPage.css'

const FEATURES = [
  { icon: BookOpen, title: '읽은 것, 바로 저장', subtitle: 'URL·PDF·메모를 한 곳에' },
  { icon: MessageCircle, title: '내 기억과 대화', subtitle: 'AI가 내 스크랩을 기억해요' },
  { icon: PenTool, title: '하루 돌아보기', subtitle: '성찰 질문으로 쉽게 시작' },
  { icon: Network, title: '연결된 지식 발견', subtitle: '기억이 쌓이면 패턴이 보여요' },
]

export default function LandingPage() {
  const navigate = useNavigate()
  const { signInWithGoogle, signInWithKakao } = useAuth()
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [error, setError] = useState('')

  const handleOAuth = async (provider: 'google' | 'kakao') => {
    setError('')
    setIsSubmitting(true)
    try {
      if (provider === 'google') {
        await signInWithGoogle()
      } else {
        await signInWithKakao()
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : '로그인 중 오류가 발생했습니다.')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="landing-page">
      {/* 좌측: 브랜드 + 피처 */}
      <div className="landing-left">
        <div className="landing-left-glow" />
        <div className="landing-left-content">
          <img src="/favicon.png" alt="Memoir" className="landing-logo-img" />
          <h1 className="landing-headline">
            기억을 모으면,<br />나만의 지식이 됩니다
          </h1>
          <p className="landing-subtext">
            매일 읽고, 생각하고, 느낀 것들 — 그냥 흘려보내지 마세요.<br />
            Memoir가 당신의 기억을 지키고, 연결하고, 되살려 드려요.
          </p>
          <div className="landing-features-mini">
            {FEATURES.map((f) => (
              <div key={f.title} className="landing-feature-mini-card">
                <div className="landing-feature-mini-icon">
                  <f.icon size={18} />
                </div>
                <div className="landing-feature-mini-text">
                  <span className="landing-feature-mini-title">{f.title}</span>
                  <span className="landing-feature-mini-sub">{f.subtitle}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* 우측: 로그인 */}
      <div className="landing-right">
        <div className="landing-auth-card">
          <div className="landing-auth-header">
            <h2>시작하기</h2>
            <p>30초면 충분해요</p>
          </div>

          <div className="landing-oauth-section">
            <button
              type="button"
              className="landing-oauth-btn landing-google-btn"
              onClick={() => handleOAuth('google')}
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
              className="landing-oauth-btn landing-kakao-btn"
              onClick={() => handleOAuth('kakao')}
              disabled={isSubmitting}
            >
              <svg viewBox="0 0 24 24" width="18" height="18" fill="#3c1e1e">
                <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
              </svg>
              카카오로 시작하기
            </button>
          </div>

          {error && <div className="landing-auth-error">{error}</div>}

          <div className="landing-divider">
            <span>또는</span>
          </div>

          <button
            type="button"
            className="landing-demo-btn"
            onClick={() => navigate('/demo')}
          >
            먼저 둘러보기 →
          </button>
        </div>

        <footer className="landing-footer">
          &copy; 2026 Memoir
        </footer>
      </div>
    </div>
  )
}
