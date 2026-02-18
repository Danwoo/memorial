import { createContext, useContext, useMemo } from 'react'
import type { ReactNode } from 'react'

interface DemoContextValue {
  isDemoMode: boolean
}

const DemoContext = createContext<DemoContextValue>({ isDemoMode: false })

// eslint-disable-next-line react-refresh/only-export-components
export function useDemoMode(): DemoContextValue {
  return useContext(DemoContext)
}

export function DemoProvider({ children, demo = false }: { children: ReactNode; demo?: boolean }) {
  const value = useMemo(() => ({ isDemoMode: demo }), [demo])
  return <DemoContext.Provider value={value}>{children}</DemoContext.Provider>
}
