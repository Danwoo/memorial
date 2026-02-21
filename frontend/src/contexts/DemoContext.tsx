import { createContext, useContext, useEffect, useMemo } from 'react'
import type { ReactNode } from 'react'

interface DemoContextValue {
  isDemoMode: boolean
}

const DemoContext = createContext<DemoContextValue>({ isDemoMode: false })

let _isDemoMode = false

// eslint-disable-next-line react-refresh/only-export-components
export function isDemoMode(): boolean {
  return _isDemoMode
}

// eslint-disable-next-line react-refresh/only-export-components
export const DEMO_USER = {
  id: '00000000-0000-0000-0000-000000000000',
  email: 'demo@memoir.app',
  full_name: '데모 사용자',
  avatar_url: undefined,
}

// eslint-disable-next-line react-refresh/only-export-components
export function useDemoMode(): DemoContextValue {
  return useContext(DemoContext)
}

export function DemoProvider({ children, demo = false }: { children: ReactNode; demo?: boolean }) {
  useEffect(() => {
    _isDemoMode = demo
    return () => { _isDemoMode = false }
  }, [demo])

  const value = useMemo(() => ({ isDemoMode: demo }), [demo])
  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}
