import { get } from './client'
import type { User } from '../types'

/** Fetch the current authenticated user's profile */
export function fetchCurrentUser(): Promise<User> {
  return get<User>('/auth/me')
}
