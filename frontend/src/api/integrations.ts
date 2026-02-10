import { get, post, put } from './client'

// ─── Types ───────────────────────────────────────────────────────────────────

export interface ProviderInfo {
  provider: string
  identity_id: string
  email: string | null
  created_at: string | null
}

export interface IntegrationStatus {
  email: string | null
  providers: ProviderInfo[]
  kakao_channel: string
  chrome_extension: string
  bot_enabled: boolean
  bot_delivery_hour: number | null
}

export interface DeliveryLogEntry {
  digest_date: string
  status: 'success' | 'failed' | 'token_expired' | 'no_content'
  error_message: string | null
  delivered_at: string
}

export interface BotSettings {
  enabled: boolean
  delivery_hour: number
  include_memories: boolean
  include_journals: boolean
  include_insights: boolean
  last_delivery: DeliveryLogEntry | null
}

export interface BotSettingsUpdate {
  enabled?: boolean
  delivery_hour?: number
  include_memories?: boolean
  include_journals?: boolean
  include_insights?: boolean
}

// ─── API Functions ───────────────────────────────────────────────────────────

export async function getIntegrationStatus(): Promise<IntegrationStatus> {
  return get<IntegrationStatus>('/integrations/status')
}

export async function storeProviderToken(
  providerToken: string,
  providerRefreshToken?: string | null,
): Promise<{ success: boolean; message: string }> {
  return post<{ success: boolean; message: string }>('/integrations/store-provider-token', {
    provider_token: providerToken,
    provider_refresh_token: providerRefreshToken ?? null,
  })
}

export async function getBotSettings(): Promise<BotSettings> {
  return get<BotSettings>('/integrations/bot-settings')
}

export async function updateBotSettings(settings: BotSettingsUpdate): Promise<BotSettings> {
  return put<BotSettings>('/integrations/bot-settings', settings)
}
