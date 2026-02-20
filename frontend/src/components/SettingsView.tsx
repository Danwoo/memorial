import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useToast } from '../contexts/ToastContext'
import { getNotificationSettings, updateNotificationSetting } from '../api/notifications'
import type { NudgeSetting } from '../api/notifications'
import { fetchExportCounts, exportMemories, exportJournals, exportAll } from '../api/export'
import type { ExportCounts } from '../api/export'
import { usePushNotifications } from '../hooks/usePushNotifications'
import { usePWAInstall } from '../hooks/usePWAInstall'
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
  const { user } = useAuth()
  const { preference: themePreference, setPreference: setThemePreference } = useTheme()
  const toast = useToast()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [activeTab, setActiveTab] = useState<SettingsTab>('integrations')

  // 알림 (넛지) 설정
  const [nudgeSettings, setNudgeSettings] = useState<NudgeSetting[]>([])
  const [nudgeLoading, setNudgeLoading] = useState(false)
  const { isSupported: pushSupported, isSubscribed: pushSubscribed, isLoading: pushLoading, subscribe: subscribePush } = usePushNotifications()
  const { canInstall, isInstalled, install: installPWA } = usePWAInstall()

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

  // 알림 설정 + 내보내기 데이터 로드
  const loadData = useCallback(async () => {
    const [nudgeResult, exportResult] = await Promise.allSettled([
      getNotificationSettings(),
      fetchExportCounts(),
    ])
    if (nudgeResult.status === 'fulfilled') setNudgeSettings(nudgeResult.value.nudges)
    if (exportResult.status === 'fulfilled') setExportCounts(exportResult.value)
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

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

  // ─── 메인 렌더 ────────────────────────────────────────────────────────────
  return (
    <div className="settings-view">
      <ProfileSection
        user={user}
        email={user?.email ?? null}
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
      {activeTab === 'integrations' && <IntegrationsTab />}
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
