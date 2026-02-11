import { get } from './client'
import type { User } from '../types'

// 현재 인증된 사용자 프로필 조회
export function fetchCurrentUser(): Promise<User> {
  return get<User>('/auth/me')
}
