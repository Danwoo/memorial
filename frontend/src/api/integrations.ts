import { get, post } from './client'

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
