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
import { usePWAInstall } from '../hooks/usePWAInstall'
import type { ProviderInfo, BotSettings, BotSettingsUpdate, ChannelLinkCode, ChannelStatus } from '../api/integrations'
import './SettingsView.css'

const PROVIDER_LABELS: Record<string, string> = {
  google: 'Google',
  kakao: 'Kakao',
}

const SUPPORTED_PROVIDERS = ['google', 'kakao'] as const

type SettingsTab = 'notifications' | 'integrations' | 'data'

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
  const [activeTab, setActiveTab] = useState<SettingsTab>('integrations')

  // 알림 (넛지) 설정
  const [nudgeSettings, setNudgeSettings] = useState<NudgeSetting[]>([])
  const [nudgeLoading, setNudgeLoading] = useState(false)
  const { isSupported: pushSupported, isSubscribed: pushSubscribed, isLoading: pushLoading, subscribe: subscribePush } = usePushNotifications()
  const { canInstall, isInstalled, install: installPWA } = usePWAInstall()

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
  const KAKAO_CHANNEL_CHAT_URL = 'https://pf.kakao.com/_NxoGzX/chat'

  const handleGenerateLinkCode = async () => {
    try {
      setChannelLoading(true)
      const result = await generateChannelLinkCode()
      setLinkCode(result)
      startCountdown(result.expires_at)

      const command = `#연결 ${result.code}`
      try {
        await navigator.clipboard.writeText(command)
        toast.success('연결 코드가 클립보드에 복사되었습니다!')
      } catch {
        // 클립보드 실패 시 무시
      }
    } catch {
      toast.error('연결 코드 생성에 실패했습니다')
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

  // ─── 테마 순환 ──────────────────────────────────────────────────────────
  const themeOptions: { value: ThemePreference; icon: JSX.Element; label: string }[] = [
    {
      value: 'light',
      label: '라이트',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/>
          <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
          <line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/>
          <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
        </svg>
      ),
    },
    {
      value: 'dark',
      label: '다크',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"/>
        </svg>
      ),
    },
    {
      value: 'system',
      label: '자동',
      icon: (
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>
        </svg>
      ),
    },
  ]

  // ─── 렌더: 알림 탭 ────────────────────────────────────────────────────────
  const renderNotificationsTab = () => (
    <div className="settings-tab-content">
      <div className="settings-card">
        {/* 브라우저 푸시 권한 */}
        <div className="setting-row">
          <div className="setting-info">
            <span className="setting-label">브라우저 알림</span>
            <span className="setting-desc">푸시 알림을 받으려면 브라우저 권한이 필요합니다</span>
          </div>
          {!pushSupported ? (
            <span className="status-badge">미지원</span>
          ) : pushSubscribed ? (
            <span className="status-badge connected">활성화됨</span>
          ) : (
            <button className="btn btn-sm btn-primary" onClick={handlePushSubscribe} disabled={pushLoading}>
              {pushLoading ? '처리 중...' : '알림 허용'}
            </button>
          )}
        </div>

        <div className="setting-row">
          <div className="setting-info">
            <span className="setting-label">저녁 회고</span>
            <span className="setting-desc">오늘 저장한 기억 수와 주요 토픽을 알려줍니다</span>
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
          <div className="setting-row setting-sub">
            <span className="setting-label">발송 시간</span>
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

        <div className="setting-row">
          <div className="setting-info">
            <span className="setting-label">주간 요약</span>
            <span className="setting-desc">매주 일요일에 이번 주 활동 통계를 보내줍니다</span>
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

        <div className="setting-row">
          <div className="setting-info">
            <span className="setting-label">기억 연결 발견</span>
            <span className="setting-desc">저장한 기억들 사이의 연결을 찾아 알려줍니다</span>
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
    </div>
  )

  // ─── 렌더: 연동 탭 ────────────────────────────────────────────────────────
  const renderIntegrationsTab = () => (
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

      {/* 카카오톡 채널 */}
      <h3 className="tab-section-title">카카오톡 채널</h3>
      <div className="settings-card">
        <div className="channel-header">
          <div className="integration-left">
            <div className="provider-icon kakao-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
              </svg>
            </div>
            <div className="integration-info">
              <span className="setting-label">채널 연결</span>
              <span className="setting-desc">카카오톡에서 URL이나 메모를 보내 바로 저장</span>
            </div>
          </div>
          {channelStatus?.connected && (
            <div className="integration-actions">
              <span className="status-badge connected">연결됨</span>
              <button className="btn btn-secondary btn-sm" onClick={handleDisconnectChannel} disabled={channelLoading}>
                {channelLoading ? '...' : '해제'}
              </button>
            </div>
          )}
        </div>

        {!channelStatus?.connected && (
          <div className="channel-connect-section">
            {linkCode ? (
              <div className="channel-link-steps">
                <div className="link-step">
                  <span className="link-step-number">1</span>
                  <div className="link-step-content">
                    <span className="link-step-label">연결 코드 복사 완료</span>
                    <div className="link-code-command"
                      onClick={async () => {
                        try {
                          await navigator.clipboard.writeText(`#연결 ${linkCode.code}`)
                          toast.success('클립보드에 복사되었습니다!')
                        } catch { /* ignore */ }
                      }}
                      title="클릭하여 다시 복사"
                    >
                      #연결 {linkCode.code}
                    </div>
                  </div>
                </div>
                <div className="link-step">
                  <span className="link-step-number">2</span>
                  <div className="link-step-content">
                    <span className="link-step-label">카카오톡에서 붙여넣기</span>
                    <a href={KAKAO_CHANNEL_CHAT_URL} target="_blank" rel="noopener noreferrer"
                      className="btn kakao-connect-btn btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', textDecoration: 'none', marginTop: '4px' }}>
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/></svg>
                      채널 열기
                    </a>
                  </div>
                </div>
                <span className="link-code-timer">남은 시간: {countdown}</span>
              </div>
            ) : (
              <div className="channel-connect-cta">
                <p className="setting-desc">카카오톡 Memoir 채널에 아무 메시지를 보내면 자동 연결 링크를 받을 수 있습니다.</p>
                <div className="channel-connect-buttons">
                  <a href={KAKAO_CHANNEL_CHAT_URL} target="_blank" rel="noopener noreferrer"
                    className="btn kakao-connect-btn btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}>
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/></svg>
                    카카오톡에서 연결
                  </a>
                  <button className="btn btn-secondary btn-sm" onClick={handleGenerateLinkCode} disabled={channelLoading}>
                    {channelLoading ? '생성 중...' : '코드로 연결'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 카카오톡 다이제스트 */}
      <div className="settings-card">
        <div className="setting-row" style={{ borderTop: 'none' }}>
          <div className="setting-info">
            <span className="setting-label">일일 다이제스트</span>
            <span className="setting-desc">매일 정해진 시간에 오늘의 기록을 카카오톡으로 전송</span>
          </div>
          {!kakaoLinked ? (
            <span className="status-badge">카카오 연결 필요</span>
          ) : (
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={botSettings?.enabled ?? false}
                onChange={(e) => handleBotSettingChange({ enabled: e.target.checked })}
                disabled={botLoading}
              />
              <span className="toggle-slider" />
            </label>
          )}
        </div>

        {kakaoLinked && botSettings?.enabled && (
          <>
            <div className="setting-row setting-sub">
              <span className="setting-label">발송 시간</span>
              <select
                value={botSettings?.delivery_hour ?? 21}
                onChange={(e) => handleBotSettingChange({ delivery_hour: Number(e.target.value) })}
                disabled={botLoading}
              >
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                ))}
              </select>
            </div>
            <div className="setting-row setting-sub">
              <span className="setting-label">포함 항목</span>
              <div className="bot-checkboxes">
                <label><input type="checkbox" checked={botSettings?.include_memories ?? true}
                  onChange={(e) => handleBotSettingChange({ include_memories: e.target.checked })} disabled={botLoading} /> 기억</label>
                <label><input type="checkbox" checked={botSettings?.include_journals ?? true}
                  onChange={(e) => handleBotSettingChange({ include_journals: e.target.checked })} disabled={botLoading} /> 일기</label>
                <label><input type="checkbox" checked={botSettings?.include_insights ?? true}
                  onChange={(e) => handleBotSettingChange({ include_insights: e.target.checked })} disabled={botLoading} /> 인사이트</label>
              </div>
            </div>
            {botSettings?.last_delivery && (
              <div className="setting-row setting-sub">
                <span className="setting-label">최근 발송</span>
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
          </>
        )}
      </div>

      {/* Chrome Extension */}
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
      </div>
    </div>
  )

  // ─── 렌더: 데이터 탭 ────────────────────────────────────────────────────────
  const renderDataTab = () => (
    <div className="settings-tab-content">
      <div className="settings-card">
        <h3 className="card-title">데이터 내보내기</h3>
        {exportCounts && (
          <p className="setting-desc" style={{ marginBottom: 'var(--space-md)' }}>
            기억 {exportCounts.memories}개, 저널 {exportCounts.journals}개
          </p>
        )}
        <div className="export-buttons">
          <button className="btn btn-sm btn-secondary" onClick={() => handleExport('memories')} disabled={exportLoading !== null}>
            {exportLoading === 'memories' ? '준비 중...' : '기억 (JSON)'}
          </button>
          <button className="btn btn-sm btn-secondary" onClick={() => handleExport('journals')} disabled={exportLoading !== null}>
            {exportLoading === 'journals' ? '준비 중...' : '저널 (Markdown)'}
          </button>
          <button className="btn btn-sm btn-secondary" onClick={() => handleExport('all')} disabled={exportLoading !== null}>
            {exportLoading === 'all' ? '준비 중...' : '전체 백업 (JSON)'}
          </button>
        </div>
      </div>

      <div className="settings-card">
        <div className="setting-row" style={{ borderTop: 'none' }}>
          <div className="setting-info">
            <span className="setting-label">온보딩 다시 보기</span>
            <span className="setting-desc">제품 소개 가이드를 다시 확인합니다</span>
          </div>
          <button className="btn btn-sm btn-secondary" onClick={() => {
            localStorage.removeItem('onboarding_completed')
            toast.info('온보딩 가이드를 다시 시작합니다')
            navigate('/chat')
            window.location.reload()
          }} type="button">
            다시 보기
          </button>
        </div>

        {(canInstall || isInstalled) && (
          <div className="setting-row">
            <div className="setting-info">
              <span className="setting-label">앱 설치하기</span>
              <span className="setting-desc">홈 화면에 추가하여 앱처럼 사용</span>
            </div>
            {isInstalled ? (
              <span className="status-badge connected">설치됨</span>
            ) : (
              <button className="btn btn-sm btn-primary" onClick={async () => {
                const accepted = await installPWA()
                if (accepted) toast.success('앱이 설치되었습니다!')
              }} type="button">
                설치
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )

  // ─── 메인 렌더 ────────────────────────────────────────────────────────────
  return (
    <div className="settings-view">
      {/* 프로필 헤더 */}
      <header className="settings-profile">
        <div className="profile-left">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="" className="profile-avatar" referrerPolicy="no-referrer" />
          ) : (
            <div className="profile-avatar-placeholder">
              {(user?.full_name || user?.email || '?')[0].toUpperCase()}
            </div>
          )}
          <div className="profile-text">
            <h1 className="profile-name">{user?.full_name || '사용자'}</h1>
            <p className="profile-email">{email ?? user?.email ?? '-'}</p>
          </div>
        </div>
        <div className="theme-toggle-group">
          {themeOptions.map((opt) => (
            <button
              key={opt.value}
              className={`theme-btn ${themePreference === opt.value ? 'theme-btn--active' : ''}`}
              onClick={() => setThemePreference(opt.value)}
              title={opt.label}
              type="button"
            >
              {opt.icon}
            </button>
          ))}
        </div>
      </header>

      {/* 탭 네비게이션 */}
      <nav className="settings-tabs">
        <button
          className={`settings-tab ${activeTab === 'integrations' ? 'settings-tab--active' : ''}`}
          onClick={() => setActiveTab('integrations')}
          type="button"
        >
          연동
        </button>
        <button
          className={`settings-tab ${activeTab === 'notifications' ? 'settings-tab--active' : ''}`}
          onClick={() => setActiveTab('notifications')}
          type="button"
        >
          알림
        </button>
        <button
          className={`settings-tab ${activeTab === 'data' ? 'settings-tab--active' : ''}`}
          onClick={() => setActiveTab('data')}
          type="button"
        >
          데이터
        </button>
      </nav>

      {/* 탭 콘텐츠 */}
      {activeTab === 'notifications' && renderNotificationsTab()}
      {activeTab === 'integrations' && renderIntegrationsTab()}
      {activeTab === 'data' && renderDataTab()}
    </div>
  )
}
