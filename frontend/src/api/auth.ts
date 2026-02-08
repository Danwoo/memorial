import { get, post } from './client'
import type { User, AuthCredentials, AuthResponse } from '../types'

/** Log in with email and password */
export function login(credentials: AuthCredentials): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/login', credentials)
}

/** Sign up with email and password */
export function signup(credentials: AuthCredentials): Promise<AuthResponse> {
  return post<AuthResponse>('/auth/signup', credentials)
}

/** Fetch the current authenticated user's profile */
export function fetchCurrentUser(): Promise<User> {
  return get<User>('/auth/me')
}
