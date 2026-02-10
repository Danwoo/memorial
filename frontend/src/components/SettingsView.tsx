import { useState, useEffect, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { getIntegrationStatus, getBotSettings, updateBotSettings } from '../api'
import type { ProviderInfo, BotSettings, BotSettingsUpdate } from '../api/integrations'
import './SettingsView.css'

const PROVIDER_LABELS: Record<string, string> = {
  google: 'Google',
  kakao: 'Kakao',
}

const SUPPORTED_PROVIDERS = ['google', 'kakao'] as const

export default function SettingsView() {
  const { user, linkProvider, unlinkProvider } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [email, setEmail] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [toast, setToast] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [botSettings, setBotSettings] = useState<BotSettings | null>(null)
  const [botLoading, setBotLoading] = useState(false)

  // Check for link callback result in URL params
  useEffect(() => {
    const linked = searchParams.get('linked')
    if (linked) {
      setToast({ type: 'success', message: `${PROVIDER_LABELS[linked] ?? linked} 계정이 연결되었습니다!` })
      searchParams.delete('linked')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams])

  // Auto-dismiss toast
  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(null), 4000)
    return () => clearTimeout(timer)
  }, [toast])

  // Load integration status + bot settings
  const loadStatus = useCallback(async () => {
    try {
      setLoading(true)
      const status = await getIntegrationStatus()
      setProviders(status.providers)
      setEmail(status.email)

      // Load bot settings in parallel
      try {
        const bot = await getBotSettings()
        setBotSettings(bot)
      } catch {
        setBotSettings(null)
      }
    } catch {
      setProviders([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadStatus()
  }, [loadStatus])

  const isProviderLinked = (provider: string) =>
    providers.some((p) => p.provider === provider)

  const getProviderIdentity = (provider: string) =>
    providers.find((p) => p.provider === provider)

  const handleLink = async (provider: 'google' | 'kakao') => {
    try {
      setActionLoading(provider)
      await linkProvider(provider)
    } catch {
      setToast({ type: 'error', message: `${PROVIDER_LABELS[provider]} 연결에 실패했습니다` })
      setActionLoading(null)
    }
  }

  const handleUnlink = async (provider: string) => {
    if (providers.length <= 1) {
      setToast({ type: 'error', message: '최소 1개의 로그인 방식이 필요합니다' })
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
      await loadStatus()
      setToast({ type: 'success', message: `${PROVIDER_LABELS[provider] ?? provider} 연결이 해제되었습니다` })
    } catch {
      setToast({ type: 'error', message: '연결 해제에 실패했습니다' })
    } finally {
      setActionLoading(null)
    }
  }

  const handleBotSettingChange = async (update: BotSettingsUpdate) => {
    try {
      setBotLoading(true)
      const updated = await updateBotSettings(update)
      setBotSettings(updated)
      setToast({ type: 'success', message: '다이제스트 설정이 저장되었습니다' })
    } catch (err) {
      const message = err instanceof Error ? err.message : '설정 저장에 실패했습니다'
      setToast({ type: 'error', message })
    } finally {
      setBotLoading(false)
    }
  }

  const kakaoLinked = isProviderLinked('kakao')
  const primaryProvider = providers.length > 0 ? providers[0].provider : null

  return (
    <div className="settings-view">
      {toast && (
        <div className={`settings-toast ${toast.type}`}>
          <span>{toast.type === 'success' ? '\u2713' : '!'}</span>
          {toast.message}
        </div>
      )}

      <header className="settings-header">
        <h1>설정</h1>
        <p className="settings-subtitle">계정 및 서비스 연동을 관리합니다</p>
      </header>

      {/* Section 1: Account Info */}
      <section className="settings-section">
        <h2 className="section-title">계정 정보</h2>
        <div className="account-info-card glass-card">
          <div className="account-info-row">
            <span className="account-info-label">이메일</span>
            <span className="account-info-value">{email ?? user?.email ?? '-'}</span>
          </div>
          <div className="account-info-row">
            <span className="account-info-label">로그인 방식</span>
            <span className="account-info-value">
              {loading ? (
                <span className="loading-text">로딩 중...</span>
              ) : (
                PROVIDER_LABELS[primaryProvider ?? ''] ?? primaryProvider ?? '-'
              )}
            </span>
          </div>
        </div>
      </section>

      {/* Section 2: Connected Accounts */}
      <section className="settings-section">
        <h2 className="section-title">연결된 계정</h2>
        {loading ? (
          <div className="loading-spinner small" />
        ) : (
          <div className="provider-list">
            {SUPPORTED_PROVIDERS.map((provider) => {
              const linked = isProviderLinked(provider)
              const isOnlyProvider = providers.length <= 1 && linked
              const isActioning = actionLoading === provider
              return (
                <div key={provider} className="provider-card glass-card">
                  <div className="provider-info">
                    <div className={`provider-icon ${provider}-icon`}>
                      {provider === 'google' && (
                        <svg viewBox="0 0 24 24" width="22" height="22">
                          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                        </svg>
                      )}
                      {provider === 'kakao' && (
                        <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                          <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
                        </svg>
                      )}
                    </div>
                    <div className="provider-details">
                      <h3>{PROVIDER_LABELS[provider]}</h3>
                      <p>{linked
                        ? (getProviderIdentity(provider)?.email ?? '연결됨')
                        : '연결되지 않음'
                      }</p>
                    </div>
                  </div>
                  <div className="provider-actions">
                    {linked ? (
                      <>
                        <span className="status-badge connected">연결됨</span>
                        <button
                          className="btn btn-secondary btn-sm"
                          onClick={() => handleUnlink(provider)}
                          disabled={isOnlyProvider || isActioning}
                          title={isOnlyProvider ? '최소 1개의 로그인 방식이 필요합니다' : undefined}
                        >
                          {isActioning ? '처리 중...' : '해제'}
                        </button>
                      </>
                    ) : (
                      <button
                        className={`btn btn-sm ${provider}-connect-btn`}
                        onClick={() => handleLink(provider)}
                        disabled={isActioning}
                      >
                        {isActioning ? '처리 중...' : '연결하기'}
                      </button>
                    )}
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* Section 3: KakaoTalk Daily Digest */}
      <section className="settings-section">
        <h2 className="section-title">서비스 연동</h2>
        <div className="provider-list">
          <div className="bot-settings-card glass-card">
            <div className="provider-info">
              <div className="provider-icon kakao-icon">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                  <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
                </svg>
              </div>
              <div className="provider-details">
                <h3>카카오톡 일일 다이제스트</h3>
                <p>매일 정해진 시간에 오늘의 기록을 카카오톡으로 받아보세요</p>
              </div>
            </div>

            {!kakaoLinked ? (
              <div className="bot-prereq-notice">
                카카오 계정 연결이 필요합니다. 위에서 Kakao 계정을 먼저 연결해주세요.
              </div>
            ) : (
              <div className="bot-controls">
                {/* Enable toggle */}
                <div className="bot-setting-row">
                  <span className="bot-setting-label">다이제스트 활성화</span>
                  <label className="toggle-switch">
                    <input
                      type="checkbox"
                      checked={botSettings?.enabled ?? false}
                      onChange={(e) => handleBotSettingChange({ enabled: e.target.checked })}
                      disabled={botLoading}
                    />
                    <span className="toggle-slider" />
                  </label>
                </div>

                {/* Delivery hour */}
                <div className="bot-setting-row">
                  <span className="bot-setting-label">발송 시간</span>
                  <select
                    value={botSettings?.delivery_hour ?? 21}
                    onChange={(e) => handleBotSettingChange({ delivery_hour: Number(e.target.value) })}
                    disabled={botLoading || !botSettings?.enabled}
                  >
                    {Array.from({ length: 24 }, (_, i) => (
                      <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                    ))}
                  </select>
                </div>

                {/* Content checkboxes */}
                <div className="bot-setting-row">
                  <span className="bot-setting-label">포함 항목</span>
                  <div className="bot-checkboxes">
                    <label>
                      <input
                        type="checkbox"
                        checked={botSettings?.include_memories ?? true}
                        onChange={(e) => handleBotSettingChange({ include_memories: e.target.checked })}
                        disabled={botLoading || !botSettings?.enabled}
                      />
                      기억
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={botSettings?.include_journals ?? true}
                        onChange={(e) => handleBotSettingChange({ include_journals: e.target.checked })}
                        disabled={botLoading || !botSettings?.enabled}
                      />
                      일기
                    </label>
                    <label>
                      <input
                        type="checkbox"
                        checked={botSettings?.include_insights ?? true}
                        onChange={(e) => handleBotSettingChange({ include_insights: e.target.checked })}
                        disabled={botLoading || !botSettings?.enabled}
                      />
                      인사이트
                    </label>
                  </div>
                </div>

                {/* Last delivery status */}
                {botSettings?.last_delivery && (
                  <div className="bot-setting-row">
                    <span className="bot-setting-label">최근 발송</span>
                    <span className={`delivery-status ${botSettings.last_delivery.status}`}>
                      {botSettings.last_delivery.status === 'success' && '발송 완료'}
                      {botSettings.last_delivery.status === 'failed' && '발송 실패'}
                      {botSettings.last_delivery.status === 'token_expired' && '토큰 만료'}
                      {botSettings.last_delivery.status === 'no_content' && '콘텐츠 없음'}
                      {' — '}
                      {new Date(botSettings.last_delivery.delivered_at).toLocaleString('ko-KR')}
                    </span>
                  </div>
                )}
              </div>
            )}
          </div>

          <div className="provider-card glass-card">
            <div className="provider-info">
              <div className="provider-icon chrome-icon">
                <svg viewBox="0 0 24 24" width="22" height="22">
                  <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2"/>
                  <circle cx="12" cy="12" r="4" fill="currentColor"/>
                </svg>
              </div>
              <div className="provider-details">
                <h3>Chrome Extension</h3>
                <p>웹 브라우징 중 기억을 빠르게 저장할 수 있습니다</p>
              </div>
            </div>
            <div className="provider-actions">
              <span className="status-badge upcoming">준비 중</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
