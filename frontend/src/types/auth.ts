/** Authenticated user information */
export interface User {
  id: string
  email: string
  role?: string
  full_name?: string
  avatar_url?: string
}

/** Credentials for login/signup */
export interface AuthCredentials {
  email: string
  password: string
}

/** Response from login/signup endpoints */
export interface AuthResponse {
  access_token: string
  user: User
}

/** Available navigation views */
export type View = 'chat' | 'memories' | 'graph' | 'search' | 'dashboard' | 'timeline' | 'journal'
