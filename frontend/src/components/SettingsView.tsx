import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useTheme, type ThemePreference } from '../contexts/ThemeContext'
import { useToast } from '../contexts/ToastContext'
import {
  getIntegrationStatus,
  getBotSettings,
  updateBotSettings,
  generateChannelLinkCode,
  getChannelStatus,
  disconnectChannel,
} from '../api'
import { getNotificationSettings, updateNotificationSetting } from '../api/notifications'
import type { NudgeSetting } from '../api/notifications'
import { fetchExportCounts, exportMemories, exportJournals, exportAll } from '../api/export'
import type { ExportCounts } from '../api/export'
import { usePushNotifications } from '../hooks/usePushNotifications'
import type { ProviderInfo, BotSettings, BotSettingsUpdate, ChannelLinkCode, ChannelStatus } from '../api/integrations'
import './SettingsView.css'

const PROVIDER_LABELS: Record<string, string> = {
  google: 'Google',
  kakao: 'Kakao',
}

const SUPPORTED_PROVIDERS = ['google', 'kakao'] as const

export default function SettingsView() {
  const { user, linkProvider, unlinkProvider } = useAuth()
  const { preference: themePreference, setPreference: setThemePreference } = useTheme()
  const toast = useToast()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const [email, setEmail] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [botSettings, setBotSettings] = useState<BotSettings | null>(null)
  const [botLoading, setBotLoading] = useState(false)

  // 알림 (넛지) 설정
  const [nudgeSettings, setNudgeSettings] = useState<NudgeSetting[]>([])
  const [nudgeLoading, setNudgeLoading] = useState(false)
  const { isSupported: pushSupported, isSubscribed: pushSubscribed, isLoading: pushLoading, subscribe: subscribePush } = usePushNotifications()

  // 카카오톡 채널 연결 상태
  const [channelStatus, setChannelStatus] = useState<ChannelStatus | null>(null)
  const [linkCode, setLinkCode] = useState<ChannelLinkCode | null>(null)
  const [channelLoading, setChannelLoading] = useState(false)
  const [countdown, setCountdown] = useState('')
  const countdownRef = useRef<ReturnType<typeof setInterval> | null>(null)

  // 데이터 내보내기
  const [exportCounts, setExportCounts] = useState<ExportCounts | null>(null)
  const [exportLoading, setExportLoading] = useState<string | null>(null)

  // URL 파라미터에서 계정 연결 결과 확인 (OAuth 콜백)
  useEffect(() => {
    const linked = searchParams.get('linked')
    if (linked) {
      toast.success(`${PROVIDER_LABELS[linked] ?? linked} 계정이 연결되었습니다!`)
      searchParams.delete('linked')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams, toast])

  // 연동 상태 + 봇 설정 + 채널 상태 로드
  const loadStatus = useCallback(async () => {
    try {
      setLoading(true)
      const status = await getIntegrationStatus()
      setProviders(status.providers)
      setEmail(status.email)

      // 봇 설정, 채널 상태, 알림 설정, 내보내기 건수를 병렬로 로드
      const [botResult, channelResult, nudgeResult, exportResult] = await Promise.allSettled([
        getBotSettings(),
        getChannelStatus(),
        getNotificationSettings(),
        fetchExportCounts(),
      ])
      if (botResult.status === 'fulfilled') setBotSettings(botResult.value)
      if (channelResult.status === 'fulfilled') setChannelStatus(channelResult.value)
      if (nudgeResult.status === 'fulfilled') setNudgeSettings(nudgeResult.value.nudges)
      if (exportResult.status === 'fulfilled') setExportCounts(exportResult.value)
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
      toast.error( `${PROVIDER_LABELS[provider]} 연결에 실패했습니다`)
      setActionLoading(null)
    }
  }

  const handleUnlink = async (provider: string) => {
    if (providers.length <= 1) {
      toast.error( '최소 1개의 로그인 방식이 필요합니다')
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
      toast.success( `${PROVIDER_LABELS[provider] ?? provider} 연결이 해제되었습니다`)
    } catch {
      toast.error( '연결 해제에 실패했습니다')
    } finally {
      setActionLoading(null)
    }
  }

  const handleBotSettingChange = async (update: BotSettingsUpdate) => {
    try {
      setBotLoading(true)
      const updated = await updateBotSettings(update)
      setBotSettings(updated)
      toast.success( '다이제스트 설정이 저장되었습니다')
    } catch (err) {
      const message = err instanceof Error ? err.message : '설정 저장에 실패했습니다'
      toast.error(message)
    } finally {
      setBotLoading(false)
    }
  }

  // ─── 넛지 알림 설정 핸들러 ──────────────────────────────────────────────
  const handleNudgeToggle = async (nudgeType: string, enabled: boolean) => {
    try {
      setNudgeLoading(true)
      const result = await updateNotificationSetting({ nudge_type: nudgeType, enabled })
      setNudgeSettings(result.nudges)
    } catch {
      toast.error('알림 설정 변경에 실패했습니다')
    } finally {
      setNudgeLoading(false)
    }
  }

  const handleNudgeHourChange = async (nudgeType: string, hour: number) => {
    try {
      setNudgeLoading(true)
      const result = await updateNotificationSetting({ nudge_type: nudgeType, delivery_hour: hour })
      setNudgeSettings(result.nudges)
    } catch {
      toast.error('발송 시간 변경에 실패했습니다')
    } finally {
      setNudgeLoading(false)
    }
  }

  const handlePushSubscribe = async () => {
    const success = await subscribePush()
    if (success) {
      toast.success('브라우저 알림이 활성화되었습니다')
    } else {
      toast.error('알림 권한을 허용해주세요')
    }
  }

  const getNudgeSetting = (type: string) =>
    nudgeSettings.find((n) => n.nudge_type === type)

  // ─── 카카오톡 채널 연결 핸들러 ──────────────────────────────────────────
  const handleGenerateLinkCode = async () => {
    try {
      setChannelLoading(true)
      const result = await generateChannelLinkCode()
      setLinkCode(result)
      startCountdown(result.expires_at)
    } catch {
      toast.error( '연결 코드 생성에 실패했습니다')
    } finally {
      setChannelLoading(false)
    }
  }

  const handleDisconnectChannel = async () => {
    try {
      setChannelLoading(true)
      await disconnectChannel()
      setChannelStatus({ connected: false, bot_user_key: null, linked_at: null })
      toast.success( '카카오톡 채널 연결이 해제되었습니다')
    } catch {
      toast.error( '채널 연결 해제에 실패했습니다')
    } finally {
      setChannelLoading(false)
    }
  }

  // ─── 데이터 내보내기 핸들러 ────────────────────────────────────────────────
  const handleExport = async (type: 'memories' | 'journals' | 'all') => {
    setExportLoading(type)
    toast.info('내보내기를 준비하고 있습니다...')
    try {
      if (type === 'memories') await exportMemories()
      else if (type === 'journals') await exportJournals()
      else await exportAll()
      toast.success('다운로드가 시작됩니다')
    } catch {
      toast.error('내보내기에 실패했습니다')
    } finally {
      setExportLoading(null)
    }
  }

  // 연결 코드 만료까지 남은 시간 카운트다운
  const startCountdown = (expiresAt: string) => {
    if (countdownRef.current) clearInterval(countdownRef.current)
    const update = () => {
      const diff = new Date(expiresAt).getTime() - Date.now()
      if (diff <= 0) {
        setCountdown('만료됨')
        setLinkCode(null)
        if (countdownRef.current) clearInterval(countdownRef.current)
        return
      }
      const min = Math.floor(diff / 60000)
      const sec = Math.floor((diff % 60000) / 1000)
      setCountdown(`${min}:${String(sec).padStart(2, '0')}`)
    }
    update()
    countdownRef.current = setInterval(update, 1000)
  }

  useEffect(() => {
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current)
    }
  }, [])

  const kakaoLinked = isProviderLinked('kakao')
  const primaryProvider = providers.length > 0 ? providers[0].provider : null

  return (
    <div className="settings-view">
      <header className="settings-header">
        <h1>설정</h1>
        <p className="settings-subtitle">계정 및 서비스 연동을 관리합니다</p>
      </header>

      {/* 계정 정보 섹션 */}
      <section className="settings-section">
        <h2 className="section-title">계정 정보</h2>
        <div className="account-info-card card">
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

      {/* 테마 설정 섹션 */}
      <section className="settings-section">
        <h2 className="section-title">테마</h2>
        <div className="theme-selector card">
          {([
            { value: 'system' as ThemePreference, label: '시스템', desc: 'OS 설정에 따라 자동 전환' },
            { value: 'light' as ThemePreference, label: '라이트', desc: '밝은 테마' },
            { value: 'dark' as ThemePreference, label: '다크', desc: '어두운 테마' },
          ]).map((option) => (
            <label key={option.value} className={`theme-option ${themePreference === option.value ? 'theme-option--active' : ''}`}>
              <input
                type="radio"
                name="theme"
                value={option.value}
                checked={themePreference === option.value}
                onChange={() => setThemePreference(option.value)}
              />
              <div className="theme-option__content">
                <span className="theme-option__label">{option.label}</span>
                <span className="theme-option__desc">{option.desc}</span>
              </div>
            </label>
          ))}
        </div>
      </section>

      {/* 기타 섹션 */}
      <section className="settings-section">
        <h2 className="section-title">기타</h2>
        <div className="card" style={{ padding: 'var(--space-md) var(--space-xl)' }}>
          <div className="bot-setting-row" style={{ borderTop: 'none' }}>
            <div className="nudge-info">
              <span className="bot-setting-label">온보딩 다시 보기</span>
              <span className="nudge-desc">제품 소개 가이드를 다시 확인합니다</span>
            </div>
            <button
              className="btn btn-sm btn-secondary"
              onClick={() => {
                localStorage.removeItem('onboarding_completed')
                toast.info('온보딩 가이드를 다시 시작합니다')
                navigate('/')
                window.location.reload()
              }}
              type="button"
            >
              다시 보기
            </button>
          </div>
        </div>
      </section>

      {/* 데이터 관리 섹션 */}
      <section className="settings-section">
        <h2 className="section-title">데이터 관리</h2>
        <div className="card" style={{ padding: 'var(--space-md) var(--space-xl)' }}>
          {exportCounts && (
            <p className="export-counts-info">
              기억 {exportCounts.memories}개, 저널 {exportCounts.journals}개
            </p>
          )}
          <div className="export-buttons">
            <button
              className="btn btn-sm btn-secondary"
              onClick={() => handleExport('memories')}
              disabled={exportLoading !== null}
              type="button"
            >
              {exportLoading === 'memories' ? '준비 중...' : '기억 내보내기 (JSON)'}
            </button>
            <button
              className="btn btn-sm btn-secondary"
              onClick={() => handleExport('journals')}
              disabled={exportLoading !== null}
              type="button"
            >
              {exportLoading === 'journals' ? '준비 중...' : '저널 내보내기 (Markdown)'}
            </button>
            <button
              className="btn btn-sm btn-secondary"
              onClick={() => handleExport('all')}
              disabled={exportLoading !== null}
              type="button"
            >
              {exportLoading === 'all' ? '준비 중...' : '전체 백업 (JSON)'}
            </button>
          </div>
        </div>
      </section>

      {/* 알림 설정 섹션 */}
      <section className="settings-section">
        <h2 className="section-title">알림</h2>
        <div className="notification-settings card">
          {/* 브라우저 푸시 권한 */}
          <div className="bot-setting-row">
            <div className="nudge-info">
              <span className="bot-setting-label">브라우저 알림</span>
              <span className="nudge-desc">푸시 알림을 받으려면 브라우저 권한이 필요합니다</span>
            </div>
            {!pushSupported ? (
              <span className="status-badge">미지원</span>
            ) : pushSubscribed ? (
              <span className="status-badge connected">활성화됨</span>
            ) : (
              <button
                className="btn btn-sm btn-primary"
                onClick={handlePushSubscribe}
                disabled={pushLoading}
              >
                {pushLoading ? '처리 중...' : '알림 허용'}
              </button>
            )}
          </div>

          <hr className="nudge-divider" />

          {/* 저녁 회고 */}
          <div className="bot-setting-row">
            <div className="nudge-info">
              <span className="bot-setting-label">저녁 회고</span>
              <span className="nudge-desc">오늘 저장한 기억 수와 주요 토픽을 알려줍니다</span>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={getNudgeSetting('evening_review')?.enabled ?? true}
                onChange={(e) => handleNudgeToggle('evening_review', e.target.checked)}
                disabled={nudgeLoading}
              />
              <span className="toggle-slider" />
            </label>
          </div>

          {getNudgeSetting('evening_review')?.enabled && (
            <div className="bot-setting-row nudge-sub-setting">
              <span className="bot-setting-label">발송 시간</span>
              <select
                value={getNudgeSetting('evening_review')?.delivery_hour ?? 21}
                onChange={(e) => handleNudgeHourChange('evening_review', Number(e.target.value))}
                disabled={nudgeLoading}
              >
                {Array.from({ length: 5 }, (_, i) => i + 19).map((h) => (
                  <option key={h} value={h}>{String(h).padStart(2, '0')}:00</option>
                ))}
              </select>
            </div>
          )}

          <hr className="nudge-divider" />

          {/* 주간 요약 */}
          <div className="bot-setting-row">
            <div className="nudge-info">
              <span className="bot-setting-label">주간 요약</span>
              <span className="nudge-desc">매주 일요일에 이번 주 활동 통계를 보내줍니다</span>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={getNudgeSetting('weekly_summary')?.enabled ?? true}
                onChange={(e) => handleNudgeToggle('weekly_summary', e.target.checked)}
                disabled={nudgeLoading}
              />
              <span className="toggle-slider" />
            </label>
          </div>

          <hr className="nudge-divider" />

          {/* 연결 발견 */}
          <div className="bot-setting-row">
            <div className="nudge-info">
              <span className="bot-setting-label">기억 연결 발견</span>
              <span className="nudge-desc">저장한 기억들 사이의 연결을 찾아 알려줍니다</span>
            </div>
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={getNudgeSetting('connection_found')?.enabled ?? true}
                onChange={(e) => handleNudgeToggle('connection_found', e.target.checked)}
                disabled={nudgeLoading}
              />
              <span className="toggle-slider" />
            </label>
          </div>
        </div>
      </section>

      {/* 연결된 계정 섹션 */}
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
                <div key={provider} className="provider-card card">
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

      {/* 서비스 연동 섹션 */}
      <section className="settings-section">
        <h2 className="section-title">서비스 연동</h2>
        <div className="provider-list">

          {/* 카카오톡 채널 연결 */}
          <div className="bot-settings-card card">
            <div className="provider-info">
              <div className="provider-icon kakao-icon">
                <svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor">
                  <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
                </svg>
              </div>
              <div className="provider-details">
                <h3>카카오톡 채널 연결</h3>
                <p>카카오톡에서 URL이나 메모를 보내 Memoir에 바로 저장하세요</p>
              </div>
            </div>

            {channelStatus?.connected ? (
              <div className="channel-connected">
                <div className="channel-status-row">
                  <span className="status-badge connected">연결됨</span>
                  <span className="channel-linked-at">
                    {channelStatus.linked_at && new Date(channelStatus.linked_at).toLocaleDateString('ko-KR')}
                  </span>
                </div>
                <button
                  className="btn btn-secondary btn-sm"
                  onClick={handleDisconnectChannel}
                  disabled={channelLoading}
                >
                  {channelLoading ? '처리 중...' : '연결 해제'}
                </button>
              </div>
            ) : linkCode ? (
              <div className="channel-link-code">
                <div className="link-code-display">{linkCode.code}</div>
                <p className="link-code-instruction">
                  카카오톡에서 Memoir 채널에 다음 메시지를 보내주세요:
                </p>
                <div className="link-code-command">#연결 {linkCode.code}</div>
                <span className="link-code-timer">남은 시간: {countdown}</span>
              </div>
            ) : (
              <div className="channel-connect-action">
                <button
                  className="btn kakao-connect-btn btn-sm"
                  onClick={handleGenerateLinkCode}
                  disabled={channelLoading}
                >
                  {channelLoading ? '생성 중...' : '연결 코드 생성'}
                </button>
              </div>
            )}
          </div>

          {/* 카카오톡 일일 다이제스트 */}
          <div className="bot-settings-card card">
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

          <div className="provider-card card">
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
