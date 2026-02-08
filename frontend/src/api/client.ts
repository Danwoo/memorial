import type { ApiError } from '../types'

const API_BASE = import.meta.env.VITE_API_URL ?? '/api/v1'

/**
 * Retrieves the current auth token from localStorage.
 * Returns null if no token is stored.
 */
function getAuthToken(): string | null {
  return localStorage.getItem('auth_token')
}

/**
 * Builds request headers with JSON content type and optional auth token.
 */
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

/**
 * Custom error class for API responses with non-OK status codes.
 */
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

/**
 * Handles non-OK responses by parsing the error body and throwing ApiResponseError.
 */
async function handleErrorResponse(res: Response): Promise<never> {
  let detail = `Request failed with status ${res.status}`
  try {
    const body: ApiError = await res.json()
    if (body.detail) {
      detail = body.detail
    }
  } catch {
    // Response body was not JSON; use the default message
  }
  throw new ApiResponseError(res.status, detail)
}

// ─── Public API ────────────────────────────────────────────────────────────────

/**
 * Type-safe GET request that returns parsed JSON.
 */
export async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: buildHeaders(),
  })

  if (!res.ok) await handleErrorResponse(res)
  return res.json() as Promise<T>
}

/**
 * Type-safe POST request that sends JSON and returns parsed JSON.
 */
export async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: buildHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) await handleErrorResponse(res)
  return res.json() as Promise<T>
}

/**
 * POST request that returns the raw Response object.
 * Useful for SSE streaming endpoints where we need to read the body progressively.
 */
export async function postRaw(
  path: string,
  body?: unknown,
  signal?: AbortSignal,
): Promise<Response> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: buildHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
    signal,
  })

  if (!res.ok) await handleErrorResponse(res)
  return res
}

/**
 * Type-safe PUT request that sends JSON and returns parsed JSON.
 */
export async function put<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'PUT',
    headers: buildHeaders(),
    body: body !== undefined ? JSON.stringify(body) : undefined,
  })

  if (!res.ok) await handleErrorResponse(res)
  return res.json() as Promise<T>
}

/**
 * Type-safe DELETE request.
 */
export async function del<T = void>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'DELETE',
    headers: buildHeaders(),
  })

  if (!res.ok) await handleErrorResponse(res)

  // Some DELETE endpoints return no content
  const text = await res.text()
  if (!text) return undefined as T
  return JSON.parse(text) as T
}
