/* eslint-disable react-refresh/only-export-components */
import { createContext, useCallback, useContext, useState } from 'react'
import type { ReactNode } from 'react'

interface ChatSessionContextType {
  refreshFlag: number
  triggerRefresh: () => void
}

const ChatSessionContext = createContext<ChatSessionContextType>({
  refreshFlag: 0,
  triggerRefresh: () => {},
})

export function ChatSessionProvider({ children }: { children: ReactNode }) {
  const [refreshFlag, setRefreshFlag] = useState(0)
  const triggerRefresh = useCallback(() => setRefreshFlag(f => f + 1), [])

  return (
    <ChatSessionContext.Provider value={{ refreshFlag, triggerRefresh }}>
      {children}
    </ChatSessionContext.Provider>
  )
}

export function useChatSession() {
  return useContext(ChatSessionContext)
}
