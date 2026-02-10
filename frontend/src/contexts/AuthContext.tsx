import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import type { ReactNode } from 'react'
import type { Session, UserIdentity } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { storeProviderToken } from '../api'
import type { User } from '../types'

// ─── Types ───────────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: User | null
  session: Session | null
  isLoading: boolean
  signInWithGoogle: () => Promise<void>
  signInWithKakao: () => Promise<void>
  signOut: () => Promise<void>
  linkProvider: (provider: 'google' | 'kakao') => Promise<void>
  unlinkProvider: (identity: UserIdentity) => Promise<void>
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

          // Capture provider_token from Kakao OAuth and store it
          if (newSession.provider_token) {
            storeProviderToken(
              newSession.provider_token,
              newSession.provider_refresh_token,
            ).catch(() => {
              // Non-critical: token storage failure doesn't block auth
            })
          }
        } else {
          setUser(null)
        }
      },
    )

    return () => {
      subscription.unsubscribe()
    }
  }, [syncTokenToStorage])

  // ── Auth methods ────────────────────────────────────────────────────────

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

  const signOut = useCallback(async () => {
    if (supabase) {
      await supabase.auth.signOut()
    }
    syncTokenToStorage(null)
    setUser(null)
    setSession(null)
  }, [syncTokenToStorage])

  // ── Provider linking ──────────────────────────────────────────────────

  const linkProvider = useCallback(async (provider: 'google' | 'kakao') => {
    if (!supabase) {
      throw new Error('Supabase is not configured')
    }
    const options: { redirectTo: string; scopes?: string } = {
      redirectTo: `${window.location.origin}/settings?linked=${provider}`,
    }
    if (provider === 'kakao') {
      options.scopes = 'account_email profile_nickname talk_message'
    }
    const { error } = await supabase.auth.linkIdentity({
      provider,
      options,
    })
    if (error) throw error
  }, [])

  const unlinkProvider = useCallback(async (identity: UserIdentity) => {
    if (!supabase) {
      throw new Error('Supabase is not configured')
    }
    const { error } = await supabase.auth.unlinkIdentity(identity)
    if (error) throw error
  }, [])

  // ── Memoized context value ──────────────────────────────────────────────

  const value = useMemo<AuthContextValue>(
    () => ({
      user, session, isLoading,
      signInWithGoogle, signInWithKakao, signOut,
      linkProvider, unlinkProvider,
    }),
    [user, session, isLoading, signInWithGoogle, signInWithKakao, signOut, linkProvider, unlinkProvider],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
