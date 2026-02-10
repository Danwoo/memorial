import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getKakaoAuthUrl, getKakaoStatus, disconnectKakao } from '../api'
import './SettingsView.css'

export default function SettingsView() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [kakaoConnected, setKakaoConnected] = useState(false)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState(false)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Check for OAuth callback result in URL params
  useEffect(() => {
    const kakaoResult = searchParams.get('kakao')
    if (kakaoResult === 'connected') {
      setToast({ type: 'success', message: '카카오톡이 연결되었습니다!' })
      searchParams.delete('kakao')
      setSearchParams(searchParams, { replace: true })
    } else if (kakaoResult === 'error') {
      const msg = searchParams.get('message') || '연결 중 오류가 발생했습니다'
      setToast({ type: 'error', message: msg })
      searchParams.delete('kakao')
      searchParams.delete('message')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  // Auto-dismiss toast
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(timer)
  }, [toast])

  // Load Kakao connection status
  useEffect(() => {
    loadKakaoStatus()
  }, [])

  const loadKakaoStatus = async () => {
    try {
      setLoading(true)
      const status = await getKakaoStatus()
      setKakaoConnected(status.connected)
    } catch {
      // If API fails, assume not connected
      setKakaoConnected(false)
    } finally {
      setLoading(false)
    }
  }

  const handleKakaoConnect = async () => {
    try {
      setActionLoading(true)
      const { auth_url } = await getKakaoAuthUrl()
      window.location.href = auth_url
    } catch {
      setToast({ type: 'error', message: '인증 URL 생성에 실패했습니다' })
      setActionLoading(false)
    }
  }

  const handleKakaoDisconnect = async () => {
    try {
      setActionLoading(true)
      await disconnectKakao()
      setKakaoConnected(false)
      setToast({ type: 'success', message: '카카오톡 연결이 해제되었습니다' })
    } catch {
      setToast({ type: 'error', message: '연결 해제에 실패했습니다' })
    } finally {
      setActionLoading(false)
    }
  }

  return (
    <div className="settings-view">
      {toast && (
        <div className={`settings-toast ${toast.type}`}>
          <span>{toast.type === 'success' ? '✓' : '!'}</span>
          {toast.message}
        </div>
      )}

      <header className="settings-header">
        <h1>설정</h1>
        <p className="settings-subtitle">서비스 연동 및 계정 설정을 관리합니다</p>
      </header>

      <section className="settings-section">
        <h2 className="section-title">서비스 연동</h2>

        <div className="integration-card glass-card">
          <div className="integration-info">
            <div className="integration-icon kakao-icon">
              <svg viewBox="0 0 24 24" width="28" height="28" fill="currentColor">
                <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
              </svg>
            </div>
            <div className="integration-details">
              <h3>카카오톡</h3>
              <p>일일 다이제스트와 리마인더를 카카오톡으로 받을 수 있습니다</p>
            </div>
          </div>

          <div className="integration-status">
            {loading ? (
              <div className="loading-spinner small" />
            ) : kakaoConnected ? (
              <>
                <span className="status-badge connected">연결됨</span>
                <button
                  className="btn btn-secondary"
                  onClick={handleKakaoDisconnect}
                  disabled={actionLoading}
                >
                  {actionLoading ? '처리 중...' : '연결 해제'}
                </button>
              </>
            ) : (
              <button
                className="btn kakao-connect-btn"
                onClick={handleKakaoConnect}
                disabled={actionLoading}
              >
                {actionLoading ? '처리 중...' : '카카오톡 연결'}
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
