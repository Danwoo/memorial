import { get, patch, post } from './client'

export interface NudgeSetting {
  nudge_type: string
  enabled: boolean
  delivery_hour: number | null
}

export interface NotificationSettingsResponse {
  nudges: NudgeSetting[]
}

export async function getNotificationSettings(): Promise<NotificationSettingsResponse> {
  return get<NotificationSettingsResponse>('/settings/notifications')
}

export async function updateNotificationSetting(body: {
  nudge_type: string
  enabled?: boolean
  delivery_hour?: number | null
}): Promise<NotificationSettingsResponse> {
  return patch<NotificationSettingsResponse>('/settings/notifications', body)
}

export async function triggerTestNudge(nudgeType: string): Promise<{ status: string }> {
  return post<{ status: string }>(`/settings/nudge/trigger/${nudgeType}`)
}
