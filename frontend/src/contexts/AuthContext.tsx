import { createContext, useContext, useState, useEffect, useCallback, useMemo } from 'react'
import type { ReactNode } from 'react'
import type { Session, UserIdentity } from '@supabase/supabase-js'
import { supabase } from '../lib/supabase'
import { storeProviderToken } from '../api'
import type { User } from '../types'

// ─── 인증 플로우 설명 ──────────────────────────────────────────────────────
// 1. Supabase OAuth (Google/Kakao) → 세션 발급 → access_token을 localStorage에 저장
// 2. API 클라이언트(client.ts)가 localStorage의 토큰을 Authorization 헤더에 자동 첨부
// 3. 카카오 로그인 시 provider_token을 백엔드에 별도 저장 (카카오톡 메시지 전송용)
// 4. onAuthStateChange로 세션 갱신/만료를 실시간 감지하여 UI 상태 동기화
// ────────────────────────────────────────────────────────────────────────────

// ─── 타입 정의 ──────────────────────────────────────────────────────────────

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

// ─── Context 생성 ────────────────────────────────────────────────────────────

const AuthContext = createContext<AuthContextValue | null>(null)

// eslint-disable-next-line react-refresh/only-export-components
export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return ctx
}

// ─── Provider 컴포넌트 ──────────────────────────────────────────────────────

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null)
  const [session, setSession] = useState<Session | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // Supabase 토큰을 localStorage에 동기화 (API 클라이언트에서 사용)
  const syncTokenToStorage = useCallback((accessToken: string | null) => {
    if (accessToken) {
      localStorage.setItem('auth_token', accessToken)
    } else {
      localStorage.removeItem('auth_token')
    }
  }, [])

  // ── Supabase 인증 상태 변화 감지 ──────────────────────────────────────────

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

          // 카카오 OAuth에서 받은 provider_token을 백엔드에 저장
          if (newSession.provider_token) {
            storeProviderToken(
              newSession.provider_token,
              newSession.provider_refresh_token,
            ).catch(() => {
              // 비필수 작업: 토큰 저장 실패가 인증 흐름을 막지 않음
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

  // ── 인증 메서드 ────────────────────────────────────────────────────────

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

  // ── 소셜 계정 연결/해제 ─────────────────────────────────────────────

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

  // ── 메모이제이션된 컨텍스트 값 ──────────────────────────────────────────

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
