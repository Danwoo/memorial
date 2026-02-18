import type { ApiError } from '../types'

export const API_BASE = import.meta.env.VITE_API_URL ?? '/api/v1'

// localStorage에서 인증 토큰 조회
function getAuthToken(): string | null {
  return localStorage.getItem('auth_token')
}

// JSON Content-Type과 인증 토큰을 포함한 요청 헤더 생성
function buildHeaders(extra?: HeadersInit): Headers {
  const headers = new Headers(extra)

  if (!headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const token = getAuthToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  return headers
}

// API 응답 오류를 표현하는 커스텀 에러 클래스
export class ApiResponseError extends Error {
  status: number
  detail: string

  constructor(status: number, detail: string) {
    super(detail)
    this.name = 'ApiResponseError'
    this.status = status
    this.detail = detail
  }
}

// 실패 응답의 본문을 파싱하여 ApiResponseError로 변환
async function handleErrorResponse(res: Response): Promise<never> {
  let detail = `Request failed with status ${res.status}`
  try {
    const body: ApiError = await res.json()
    if (body.detail) {
      if (typeof body.detail === 'string') {
        detail = body.detail
      } else if (Array.isArray(body.detail)) {
        detail = body.detail.map(e => e.msg).join('; ')
      }
    }
  } catch {
    // JSON 파싱 실패 시 기본 메시지 사용
  }
  throw new ApiResponseError(res.status, detail)
}

// Fly.io 콜드 스타트 등 일시적 네트워크 오류 재시도
const MAX_RETRIES = 2
const RETRY_DELAY_MS = 1500

async function fetchWithRetry(
  url: string,
  options: RequestInit,
  retries = MAX_RETRIES,
): Promise<Response> {
  for (let attempt = 0; attempt <= retries; attempt++) {
    try {
      const res = await fetch(url, options)
      // 502/503/504는 서버 깨어나는 중 — 재시도
      if (res.status >= 502 && res.status <= 504 && attempt < retries) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS * (attempt + 1)))
        continue
      }
      return res
    } catch (err) {
      // 네트워크 에러 (서버 다운 등) — 재시도
      if (attempt < retries) {
        await new Promise((r) => setTimeout(r, RETRY_DELAY_MS * (attempt + 1)))
        continue
      }
      throw err
    }
  }
  // 도달하지 않지만 타입 안전성
  throw new Error('요청 재시도 초과')
}

// ─── 공개 API 메서드 ─────────────────────────────────────────────────────────

// 타입 안전한 GET 요청
export async function get<T>(path: string): Promise<T> {
  const res = await fetchWithRetry(`${API_BASE}${path}`, {
    headers: buildHeaders(),
  })

  if (!res.ok) await handleErrorResponse(res)
  return res.json() as Promise<T>
}

// 타입 안전한 POST 요청 (JSON 전송 및 응답)
export async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetchWithRetry(`${API_BASE}${path}`, {
    method: 'POST',
    headers: buildHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) await handleErrorResponse(res)
  return res.json() as Promise<T>
}

// SSE 스트리밍 엔드포인트용 POST 요청 (raw Response 반환)
export async function postRaw(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<Response> {
  const res = await fetchWithRetry(`${API_BASE}${path}`, {
    method: 'POST',
    headers: buildHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })

  if (!res.ok) await handleErrorResponse(res)
  return res
}

// FormData(멀티파트) POST 요청 (파일 업로드용)
export async function postFormData<T>(path: string, formData: FormData): Promise<T> {
  const headers = new Headers()
  const token = getAuthToken()
  if (token) {
    headers.set('Authorization', `Bearer ${token}`)
  }

  const res = await fetchWithRetry(`${API_BASE}${path}`, {
    method: 'POST',
    headers,
    body: formData,
  })

  if (!res.ok) await handleErrorResponse(res)
  return res.json() as Promise<T>
}

// 타입 안전한 PUT 요청 (JSON 전송 및 응답)
export async function put<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetchWithRetry(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: buildHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) await handleErrorResponse(res)
  return res.json() as Promise<T>
}

// 타입 안전한 PATCH 요청 (JSON 전송 및 응답)
export async function patch<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetchWithRetry(`${API_BASE}${path}`, {
    method: 'PATCH',
    headers: buildHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) await handleErrorResponse(res)
  return res.json() as Promise<T>
}

// 타입 안전한 DELETE 요청
export async function del<T = void>(path: string): Promise<T> {
  const res = await fetchWithRetry(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: buildHeaders(),
  })

  if (!res.ok) await handleErrorResponse(res)

  // 일부 DELETE 엔드포인트는 빈 응답을 반환
  const text = await res.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}
