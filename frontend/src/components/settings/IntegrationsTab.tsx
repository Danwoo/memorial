import { useState, useEffect, useCallback } from 'react'
import { useAuth } from '../../contexts/AuthContext'
import { useToast } from '../../contexts/ToastContext'
import { getIntegrationStatus } from '../../api'
import type { ProviderInfo } from '../../api/integrations'

const PROVIDER_LABELS: Record<string, string> = {
  google: 'Google',
  kakao: 'Kakao',
}

const SUPPORTED_PROVIDERS = ['google', 'kakao'] as const

export default function IntegrationsTab() {
  const { user, linkProvider, unlinkProvider } = useAuth()
  const toast = useToast()

  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false
    const load = async () => {
      try {
        setLoading(true)
        const status = await getIntegrationStatus()
        if (cancelled) return
        setProviders(status.providers)
      } catch {
        if (!cancelled) setProviders([])
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => { cancelled = true }
  }, [])

  const isProviderLinked = useCallback(
    (provider: string) => providers.some((p) => p.provider === provider),
    [providers],
  )

  const getProviderIdentity = useCallback(
    (provider: string) => providers.find((p) => p.provider === provider),
    [providers],
  )

  const handleLink = async (provider: 'google' | 'kakao') => {
    try {
      setActionLoading(provider)
      await linkProvider(provider)
    } catch {
      toast.error(`${PROVIDER_LABELS[provider]} 연결에 실패했습니다`)
      setActionLoading(null)
    }
  }

  const handleUnlink = async (provider: string) => {
    if (providers.length <= 1) {
      toast.error('최소 1개의 로그인 방식이 필요합니다')
      return
    }
    const identity = getProviderIdentity(provider)
    if (!identity) return

    try {
      setActionLoading(provider)
      await unlinkProvider({
        id: identity.identity_id,
        user_id: user?.id ?? '',
        identity_id: identity.identity_id,
        provider: provider,
      })
      const status = await getIntegrationStatus()
      setProviders(status.providers)
      toast.success(`${PROVIDER_LABELS[provider] ?? provider} 연결이 해제되었습니다`)
    } catch {
      toast.error('연결 해제에 실패했습니다')
    } finally {
      setActionLoading(null)
    }
  }

  return (
    <div className="settings-tab-content">
      {/* 연결된 계정 */}
      <h3 className="tab-section-title">연결된 계정</h3>
      <div className="settings-card">
        {loading ? (
          <div className="loading-spinner small" />
        ) : (
          SUPPORTED_PROVIDERS.map((provider) => {
            const linked = isProviderLinked(provider)
            const isOnlyProvider = providers.length <= 1 && linked
            const isActioning = actionLoading === provider
            return (
              <div key={provider} className="setting-row integration-row">
                <div className="integration-left">
                  <div className={`provider-icon ${provider}-icon`}>
                    {provider === 'google' && (
                      <svg viewBox="0 0 24 24" width="20" height="20">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                      </svg>
                    )}
                    {provider === 'kakao' && (
                      <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                        <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
                      </svg>
                    )}
                  </div>
                  <div className="integration-info">
                    <span className="setting-label">{PROVIDER_LABELS[provider]}</span>
                    <span className="setting-desc">
                      {linked ? (getProviderIdentity(provider)?.email ?? '연결됨') : '연결되지 않음'}
                    </span>
                  </div>
                </div>
                <div className="integration-actions">
                  {linked ? (
                    <>
                      <span className="status-badge connected">연결됨</span>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleUnlink(provider)}
                        disabled={isOnlyProvider || isActioning}
                        title={isOnlyProvider ? '최소 1개의 로그인 방식이 필요합니다' : undefined}
                      >
                        {isActioning ? '...' : '해제'}
                      </button>
                    </>
                  ) : (
                    <button
                      className={`btn btn-sm ${provider}-connect-btn`}
                      onClick={() => handleLink(provider)}
                      disabled={isActioning}
                    >
                      {isActioning ? '...' : '연결'}
                    </button>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* Chrome Extension */}
      <h3 className="tab-section-title">확장 기능</h3>
      <div className="settings-card">
        <div className="setting-row integration-row" style={{ borderTop: 'none' }}>
          <div className="integration-left">
            <div className="provider-icon chrome-icon">
              <svg viewBox="0 0 24 24" width="20" height="20">
                <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2"/>
                <circle cx="12" cy="12" r="4" fill="currentColor"/>
              </svg>
            </div>
            <div className="integration-info">
              <span className="setting-label">Chrome Extension</span>
              <span className="setting-desc">웹 브라우징 중 기억을 빠르게 저장</span>
            </div>
          </div>
          <a href="https://github.com/Danwoo/memorial/tree/main/extension" target="_blank" rel="noopener noreferrer"
            className="btn btn-sm btn-secondary" style={{ textDecoration: 'none' }}>
            설치 가이드
          </a>
        </div>
        <div className="setting-row integration-row">
          <div className="integration-left">
            <div className="provider-icon kakao-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
              </svg>
            </div>
            <div className="integration-info">
              <span className="setting-label">카카오톡 봇</span>
              <span className="setting-desc">카카오톡에서 URL이나 메모를 보내 바로 저장</span>
            </div>
          </div>
          <a href="https://pf.kakao.com/_NxoGzX/chat" target="_blank" rel="noopener noreferrer"
            className="btn btn-sm kakao-connect-btn" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}>
            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/></svg>
            채널 열기
          </a>
        </div>
      </div>
    </div>
  )
}
