import { get, patch, post } from './client'
import { isDemoMode } from '../contexts/DemoContext'

export interface NudgeSetting {
  nudge_type: string
  enabled: boolean
  delivery_hour: number | null
}

export interface NotificationSettingsResponse {
  nudges: NudgeSetting[]
}

export async function getNotificationSettings(): Promise<NotificationSettingsResponse> {
  if (isDemoMode()) return { nudges: [
    { nudge_type: 'daily_reminder', enabled: true, delivery_hour: 21 },
    { nudge_type: 'weekly_digest', enabled: true, delivery_hour: 9 },
    { nudge_type: 'connection_alert', enabled: false, delivery_hour: null },
  ] }
  return get<NotificationSettingsResponse>('/settings/notifications')
}

export async function updateNotificationSetting(body: {
  nudge_type: string
  enabled?: boolean
  delivery_hour?: number | null
}): Promise<NotificationSettingsResponse> {
  if (isDemoMode()) return { nudges: [] }
  return patch<NotificationSettingsResponse>('/settings/notifications', body)
}

export async function triggerTestNudge(nudgeType: string): Promise<{ status: string }> {
  if (isDemoMode()) return { status: 'demo' }
  return post<{ status: string }>(`/settings/nudge/trigger/${nudgeType}`)
}
