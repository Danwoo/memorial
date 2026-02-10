/** Authenticated user information */
export interface User {
  id: string
  email: string
  role?: string
  full_name?: string
  avatar_url?: string
}

/** Available navigation views */
export type View = 'chat' | 'memories' | 'graph' | 'search' | 'dashboard' | 'timeline' | 'journal'
