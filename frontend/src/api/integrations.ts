import { get, post, put, del } from './client'
import { isDemoMode } from '../contexts/DemoContext'

// ─── 타입 정의 ──────────────────────────────────────────────────────────────

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

export interface ChannelLinkCode {
  code: string
  expires_at: string
  instructions: string
}

export interface ChannelStatus {
  connected: boolean
  bot_user_key: string | null
  linked_at: string | null
}

// ─── API 함수 ───────────────────────────────────────────────────────────────

// 전체 연동 상태 조회 (계정, 채널, 봇 설정)
export async function getIntegrationStatus(): Promise<IntegrationStatus> {
  if (isDemoMode()) return {
    email: 'demo@memoir.app',
    providers: [{ provider: 'google', identity_id: 'demo', email: 'demo@memoir.app', created_at: null }],
    kakao_channel: 'disconnected',
    chrome_extension: 'not_installed',
    bot_enabled: false,
    bot_delivery_hour: null,
  }
  return get<IntegrationStatus>('/integrations/status')
}

// 카카오 OAuth 프로바이더 토큰을 서버에 저장
export async function storeProviderToken(
  providerToken: string,
  providerRefreshToken?: string | null,
): Promise<{ success: boolean; message: string }> {
  return post<{ success: boolean; message: string }>('/integrations/store-provider-token', {
    provider_token: providerToken,
    provider_refresh_token: providerRefreshToken ?? null,
  })
}

// 일일 다이제스트 봇 설정 조회
export async function getBotSettings(): Promise<BotSettings> {
  if (isDemoMode()) return {
    enabled: false,
    delivery_hour: 21,
    include_memories: true,
    include_journals: true,
    include_insights: true,
    last_delivery: null,
  }
  return get<BotSettings>('/integrations/bot-settings')
}

// 일일 다이제스트 봇 설정 업데이트
export async function updateBotSettings(settings: BotSettingsUpdate): Promise<BotSettings> {
  if (isDemoMode()) return { enabled: false, delivery_hour: 21, include_memories: true, include_journals: true, include_insights: true, last_delivery: null }
  return put<BotSettings>('/integrations/bot-settings', settings)
}

// ─── 카카오톡 채널 연결 API ─────────────────────────────────────────────────

// 카카오톡 채널 연결용 일회성 코드 생성
export async function generateChannelLinkCode(): Promise<ChannelLinkCode> {
  if (isDemoMode()) return { code: 'DEMO-CODE', expires_at: new Date(Date.now() + 300000).toISOString(), instructions: '데모 모드' }
  return post<ChannelLinkCode>('/integrations/kakao/channel/link-code')
}

// 카카오톡 채널 연결 상태 조회
export async function getChannelStatus(): Promise<ChannelStatus> {
  if (isDemoMode()) return { connected: false, bot_user_key: null, linked_at: null }
  return get<ChannelStatus>('/integrations/kakao/channel/status')
}

// 카카오톡 채널 연결 해제
export async function disconnectChannel(): Promise<void> {
  if (isDemoMode()) return
  return del('/integrations/kakao/channel/disconnect')
}

// 카카오톡 채널 토큰 기반 자동 연결 (카카오 봇에서 받은 링크로 호출)
export async function completeKakaoLinkByToken(
  token: string,
): Promise<{ success: boolean; message: string }> {
  if (isDemoMode()) return { success: false, message: '데모 모드' }
  return post<{ success: boolean; message: string }>('/integrations/kakao/channel/link-by-token', { token })
}
