import { get, post } from './client'

// ─── Types ───────────────────────────────────────────────────────────────────

interface KakaoAuthResponse {
  auth_url: string
  message: string
}

interface KakaoStatusResponse {
  connected: boolean
  message: string
}

interface SendMessageRequest {
  title: string
  content: string
  memory_id?: string
}

interface SendMessageResponse {
  success: boolean
  message: string
}

// ─── API Functions ───────────────────────────────────────────────────────────

export async function getKakaoAuthUrl(): Promise<KakaoAuthResponse> {
  return get<KakaoAuthResponse>('/integrations/kakao/auth')
}

export async function getKakaoStatus(): Promise<KakaoStatusResponse> {
  return get<KakaoStatusResponse>('/integrations/kakao/status')
}

export async function disconnectKakao(): Promise<{ success: boolean; message: string }> {
  return post<{ success: boolean; message: string }>('/integrations/kakao/disconnect')
}

export async function sendKakaoMessage(req: SendMessageRequest): Promise<SendMessageResponse> {
  return post<SendMessageResponse>('/integrations/kakao/send', req)
}
