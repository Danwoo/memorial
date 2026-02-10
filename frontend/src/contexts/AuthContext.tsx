import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import type { ReactNode } from 'react'
import type { Session } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { fetchCurrentUser } from '../api'
import type { User } from '../types'

// ─── Types ───────────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: User | null
  session: Session | null
  isLoading: boolean
  signIn: (email: string, password: string) => Promise<void>
  signUp: (email: string, password: string) => Promise<void>
  signInWithGoogle: () => Promise<void>
  signInWithKakao: () => Promise<void>
  signInAsDev: () => void
  signOut: () => Promise<void>
}

const DEV_USER: User = {
  id: 'dev-user',
  email: 'dev@example.com',
  full_name: 'Developer',
  avatar_url: '',
}

// ─── Context ─────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null)

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}

// ─── Provider ────────────────────────────────────────────────────────────────

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const syncTokenToStorage = useCallback((accessToken: string | null) => {
    if (accessToken) {
      localStorage.setItem('auth_token', accessToken)
    } else {
      localStorage.removeItem('auth_token')
    }
  }, [])

  // ── Supabase auth listener ──────────────────────────────────────────────

  useEffect(() => {
    // Check for persisted dev session
    const devSession = localStorage.getItem('dev_session')
    if (devSession === 'true') {
      setUser(DEV_USER)
      setIsLoading(false)
      return
    }

    if (!supabase) {
      setIsLoading(false)
      return
    }

    const client = supabase

    client.auth.getSession().then(({ data: { session: initialSession } }) => {
      if (initialSession) {
        setSession(initialSession)
        syncTokenToStorage(initialSession.access_token)

        const supaUser = initialSession.user
        setUser({
          id: supaUser.id,
          email: supaUser.email ?? '',
          full_name: supaUser.user_metadata?.full_name,
          avatar_url: supaUser.user_metadata?.avatar_url,
        })
      }
      setIsLoading(false)
    })

    const { data: { subscription } } = client.auth.onAuthStateChange(
      (_event, newSession) => {
        setSession(newSession)
        syncTokenToStorage(newSession?.access_token ?? null)

        if (newSession?.user) {
          const supaUser = newSession.user
          setUser({
            id: supaUser.id,
            email: supaUser.email ?? '',
            full_name: supaUser.user_metadata?.full_name,
            avatar_url: supaUser.user_metadata?.avatar_url,
          })
        } else {
          setUser(null)
        }
      },
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [syncTokenToStorage])

  // ── Fallback: token-based auth without Supabase ─────────────────────────

  useEffect(() => {
    if (supabase || localStorage.getItem('dev_session') === 'true') return

    const token = localStorage.getItem('auth_token')
    if (token) {
      fetchCurrentUser()
        .then((userData) => {
          setUser(userData)
        })
        .catch(() => {
          localStorage.removeItem('auth_token')
        })
        .finally(() => setIsLoading(false))
    }
  }, [])

  // ── Auth methods ────────────────────────────────────────────────────────

  const signIn = useCallback(async (email: string, password: string) => {
    if (supabase) {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
    } else {
      const { login } = await import('../api')
      const data = await login({ email, password })
      syncTokenToStorage(data.access_token)
      setUser(data.user)
    }
  }, [syncTokenToStorage])

  const signUp = useCallback(async (email: string, password: string) => {
    if (supabase) {
      const { error } = await supabase.auth.signUp({ email, password })
      if (error) throw error
    } else {
      const { signup } = await import('../api')
      const data = await signup({ email, password })
      syncTokenToStorage(data.access_token)
      setUser(data.user)
    }
  }, [syncTokenToStorage])

  const signInWithGoogle = useCallback(async () => {
    if (!supabase) {
      throw new Error('Supabase is not configured')
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${window.location.origin}/`,
      },
    })
    if (error) throw error
  }, [])

  const signInWithKakao = useCallback(async () => {
    if (!supabase) {
      throw new Error('Supabase is not configured')
    }
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'kakao',
      options: {
        redirectTo: `${window.location.origin}/`,
        scopes: 'account_email profile_nickname talk_message',
      },
    })
    if (error) throw error
  }, [])

  const signInAsDev = useCallback(() => {
    localStorage.setItem('dev_session', 'true')
    setUser(DEV_USER)
  }, [])

  const signOut = useCallback(async () => {
    if (supabase) {
      await supabase.auth.signOut()
    }
    localStorage.removeItem('dev_session')
    syncTokenToStorage(null)
    setUser(null)
    setSession(null)
  }, [syncTokenToStorage])

  // ── Memoized context value ──────────────────────────────────────────────

  const value = useMemo<AuthContextValue>(
    () => ({ user, session, isLoading, signIn, signUp, signInWithGoogle, signInWithKakao, signInAsDev, signOut }),
    [user, session, isLoading, signIn, signUp, signInWithGoogle, signInWithKakao, signInAsDev, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
