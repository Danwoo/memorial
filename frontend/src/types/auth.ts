export interface User {
  id: string
  email: string
  role?: string
  full_name?: string
  avatar_url?: string
}

export type View = 'chat' | 'memories' | 'graph' | 'journal' | 'settings'
