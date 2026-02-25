/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useState } from 'react'
import type { ReactNode } from 'react'

interface SocratesSessionContextType {
  refreshFlag: number
  triggerRefresh: () => void
}

const SocratesSessionContext = createContext<SocratesSessionContextType>({
  refreshFlag: 0,
  triggerRefresh: () => {},
})

export function SocratesSessionProvider({ children }: { children: ReactNode }) {
  const [refreshFlag, setRefreshFlag] = useState(0)
  const triggerRefresh = useCallback(() => setRefreshFlag(f => f + 1), [])

  return (
    <SocratesSessionContext.Provider value={{ refreshFlag, triggerRefresh }}>
      {children}
    </SocratesSessionContext.Provider>
  )
}

export function useSocratesSession() {
  return useContext(SocratesSessionContext)
}
