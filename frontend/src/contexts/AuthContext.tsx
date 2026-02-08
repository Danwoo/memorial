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
  signOut: () => Promise<void>
}

// ─── Dev bypass user ─────────────────────────────────────────────────────────

const DEV_USER: User = {
  id: 'dev-user',
  email: 'dev@example.com',
  full_name: 'Developer',
  avatar_url: '',
}

// ─── Context ─────────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null)

/**
 * Hook to access auth state and methods.
 * Must be used within an AuthProvider.
 */
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
  const isDev = import.meta.env.DEV

  const [user, setUser] = useState<User | null>(isDev ? DEV_USER : null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(!isDev)

  /**
   * Syncs the access token to localStorage so the existing API client
   * (which reads from localStorage) continues to work.
   */
  const syncTokenToStorage = useCallback((accessToken: string | null) => {
    if (accessToken) {
      localStorage.setItem('auth_token', accessToken)
    } else {
      localStorage.removeItem('auth_token')
    }
  }, [])

  // ── Supabase auth listener ──────────────────────────────────────────────

  useEffect(() => {
    if (isDev || !supabase) return

    const client = supabase

    // Get the initial session
    client.auth.getSession().then(({ data: { session: initialSession } }) => {
      if (initialSession) {
        setSession(initialSession)
        syncTokenToStorage(initialSession.access_token)

        // Map Supabase user to our User type
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

    // Listen for auth state changes (login, logout, token refresh)
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
  }, [isDev, syncTokenToStorage])

  // ── Fallback: token-based auth without Supabase ─────────────────────────

  useEffect(() => {
    if (isDev || supabase) return

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
    } else {
      setIsLoading(false)
    }
  }, [isDev])

  // ── Auth methods ────────────────────────────────────────────────────────

  const signIn = useCallback(async (email: string, password: string) => {
    if (supabase) {
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) throw error
    } else {
      // Fallback: use existing API login
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
      // Fallback: use existing API signup
      const { signup } = await import('../api')
      const data = await signup({ email, password })
      syncTokenToStorage(data.access_token)
      setUser(data.user)
    }
  }, [syncTokenToStorage])

  const signOut = useCallback(async () => {
    if (supabase) {
      await supabase.auth.signOut()
    }
    syncTokenToStorage(null)
    setUser(null)
    setSession(null)
  }, [syncTokenToStorage])

  // ── Memoized context value ──────────────────────────────────────────────

  const value = useMemo<AuthContextValue>(
    () => ({ user, session, isLoading, signIn, signUp, signOut }),
    [user, session, isLoading, signIn, signUp, signOut],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
