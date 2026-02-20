import { useState, useEffect, useCallback, useRef } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
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
import ProfileSection from './settings/ProfileSection'
import IntegrationsTab from './settings/IntegrationsTab'
import NotificationsTab from './settings/NotificationsTab'
import DataTab from './settings/DataTab'
import './SettingsView.css'

const PROVIDER_LABELS: Record<string, string> = {
  google: 'Google',
  kakao: 'Kakao',
}

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

  // ─── 카카오톡 채널 연결 핸들러 ──────────────────────────────────────────
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

  // 연결 코드 클립보드 복사 (IntegrationsTab에서 호출)
  const handleCopyLinkCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(`#연결 ${code}`)
      toast.success('클립보드에 복사되었습니다!')
    } catch { /* ignore */ }
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

  const handleOnboardingReset = () => {
    localStorage.removeItem('onboarding_completed')
    toast.info('온보딩 가이드를 다시 시작합니다')
    navigate('/chat')
    window.location.reload()
  }

  const handleInstallPWA = async () => {
    const accepted = await installPWA()
    if (accepted) toast.success('앱이 설치되었습니다!')
  }

  useEffect(() => {
    return () => {
      if (countdownRef.current) clearInterval(countdownRef.current)
    }
  }, [])

  const kakaoLinked = isProviderLinked('kakao')

  // ─── 메인 렌더 ────────────────────────────────────────────────────────────
  return (
    <div className="settings-view">
      <ProfileSection
        user={user}
        email={email}
        themePreference={themePreference}
        setThemePreference={setThemePreference}
      />

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
      {activeTab === 'integrations' && (
        <IntegrationsTab
          loading={loading}
          providers={providers}
          actionLoading={actionLoading}
          botSettings={botSettings}
          botLoading={botLoading}
          channelStatus={channelStatus}
          channelLoading={channelLoading}
          linkCode={linkCode}
          countdown={countdown}
          kakaoLinked={kakaoLinked}
          isProviderLinked={isProviderLinked}
          getProviderIdentity={getProviderIdentity}
          handleLink={handleLink}
          handleUnlink={handleUnlink}
          handleBotSettingChange={handleBotSettingChange}
          handleGenerateLinkCode={handleGenerateLinkCode}
          handleDisconnectChannel={handleDisconnectChannel}
          onCopyLinkCode={handleCopyLinkCode}
        />
      )}
      {activeTab === 'notifications' && (
        <NotificationsTab
          pushSupported={pushSupported}
          pushSubscribed={pushSubscribed}
          pushLoading={pushLoading}
          nudgeSettings={nudgeSettings}
          nudgeLoading={nudgeLoading}
          handlePushSubscribe={handlePushSubscribe}
          handleNudgeToggle={handleNudgeToggle}
          handleNudgeHourChange={handleNudgeHourChange}
        />
      )}
      {activeTab === 'data' && (
        <DataTab
          exportCounts={exportCounts}
          exportLoading={exportLoading}
          canInstall={canInstall}
          isInstalled={isInstalled}
          handleExport={handleExport}
          handleOnboardingReset={handleOnboardingReset}
          handleInstallPWA={handleInstallPWA}
        />
      )}
    </div>
  )
}
