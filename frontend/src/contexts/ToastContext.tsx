import { createContext, useContext, useState, useCallback, useMemo } from 'react'
import type { ReactNode } from 'react'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
  id: number
  type: ToastType
  message: string
}

interface ToastContextValue {
  toasts: Toast[]
  success: (message: string) => void
  error: (message: string) => void
  info: (message: string) => void
  dismiss: (id: number) => void
}

const AUTO_DISMISS_MS = 3000

const ToastContext = createContext<ToastContextValue | null>(null)

let nextId = 0

// eslint-disable-next-line react-refresh/only-export-components
export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext)
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider')
  }
  return ctx
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const dismiss = useCallback((id: number) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const addToast = useCallback((type: ToastType, message: string) => {
    const id = nextId++
    setToasts(prev => [...prev, { id, type, message }])
    setTimeout(() => dismiss(id), AUTO_DISMISS_MS)
  }, [dismiss])

  const success = useCallback((msg: string) => addToast('success', msg), [addToast])
  const error = useCallback((msg: string) => addToast('error', msg), [addToast])
  const info = useCallback((msg: string) => addToast('info', msg), [addToast])

  const value = useMemo(
    () => ({ toasts, success, error, info, dismiss }),
    [toasts, success, error, info, dismiss],
  )

  return (
    <ToastContext.Provider value={value}>
      {children}
      {toasts.length > 0 && (
        <div className="toast-container" aria-live="polite" aria-atomic="true" role="status">
          {toasts.map(toast => (
            <div key={toast.id} className={`toast toast-${toast.type}`} role="alert">
              <span className="toast-icon" aria-hidden="true">
                {toast.type === 'success' && '✓'}
                {toast.type === 'error' && '✕'}
                {toast.type === 'info' && 'ℹ'}
              </span>
              <span className="toast-message">{toast.message}</span>
              <button className="toast-close" onClick={() => dismiss(toast.id)} aria-label="알림 닫기">×</button>
            </div>
          ))}
        </div>
      )}
    </ToastContext.Provider>
  )
}
