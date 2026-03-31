import { useState, useEffect, useCallback } from 'react'
import { useSearchParams, useNavigate } from 'react-router-dom'
import { demoPath } from '../utils/demoPath'
import { useAuth } from '../contexts/AuthContext'
import { useTheme } from '../contexts/ThemeContext'
import { useToast } from '../contexts/ToastContext'
import { getNotificationSettings, updateNotificationSetting } from '../api/notifications'
import type { NudgeSetting } from '../api/notifications'
import { usePushNotifications } from '../hooks/usePushNotifications'
import { usePWAInstall } from '../hooks/usePWAInstall'
import ProfileSection from './settings/ProfileSection'
import IntegrationsTab from './settings/IntegrationsTab'
import NotificationsTab from './settings/NotificationsTab'
import DataTab from './settings/DataTab'
import './SettingsView.css'

export default function SettingsView() {
  const { user } = useAuth()
  const { preference: themePreference, setPreference: setThemePreference } = useTheme()
  const toast = useToast()
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()

  // 알림 (넛지) 설정
  const [nudgeSettings, setNudgeSettings] = useState<NudgeSetting[]>([])
  const [nudgeLoading, setNudgeLoading] = useState(false)
  const { isSupported: pushSupported, isSubscribed: pushSubscribed, isLoading: pushLoading, subscribe: subscribePush } = usePushNotifications()
  const { canInstall, isInstalled, install: installPWA } = usePWAInstall()

  // URL 파라미터에서 계정 연결 결과 확인 (OAuth 콜백)
  useEffect(() => {
    const linked = searchParams.get('linked')
    if (linked) {
      const label = linked === 'google' ? 'Google' : linked === 'kakao' ? 'Kakao' : linked
      toast.success(`${label} 계정이 연결되었습니다!`)
      searchParams.delete('linked')
      setSearchParams(searchParams, { replace: true })
    }
  }, [searchParams, setSearchParams, toast])

  // 알림 설정 로드
  const loadData = useCallback(async () => {
    try {
      const result = await getNotificationSettings()
      setNudgeSettings(result.nudges)
    } catch { /* silent */ }
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

  const handleOnboardingReset = () => {
    localStorage.removeItem('onboarding_completed')
    localStorage.removeItem('memoir:onboarded')
    toast.info('온보딩 가이드를 다시 시작합니다')
    navigate(demoPath('/calendar'))
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

      <section className="settings-section">
        <h2 className="settings-section-title">연동</h2>
        <IntegrationsTab />
      </section>

      <section className="settings-section">
        <h2 className="settings-section-title">알림</h2>
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
      </section>

      <section className="settings-section">
        <h2 className="settings-section-title">데이터</h2>
        <DataTab
          canInstall={canInstall}
          isInstalled={isInstalled}
          handleOnboardingReset={handleOnboardingReset}
          handleInstallPWA={handleInstallPWA}
        />
      </section>
    </div>
  )
}
