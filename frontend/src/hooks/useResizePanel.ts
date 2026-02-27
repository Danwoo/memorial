import { useState, useRef, useCallback, useEffect } from 'react'

function clampVal(val: number, min: number, max: number) {
  return Math.max(min, Math.min(max, val))
}

/**
 * 패널 드래그 리사이즈 훅.
 * direction: 'right' = 핸들이 오른쪽 → 마우스 오른쪽 이동 시 패널 확장
 *            'left'  = 핸들이 왼쪽  → 마우스 왼쪽  이동 시 패널 확장
 * storageKey: localStorage 키 (제공 시 너비 저장/복원)
 */
export function useResizePanel(
  defaultWidth: number,
  minWidth: number,
  maxWidth: number,
  direction: 'left' | 'right' = 'right',
  storageKey?: string,
) {
  const [width, setWidth] = useState(() => {
    if (storageKey) {
      const stored = localStorage.getItem(storageKey)
      if (stored) return clampVal(Number(stored), minWidth, maxWidth)
    }
    return defaultWidth
  })

  const dragRef = useRef<{ startX: number; startW: number } | null>(null)

  useEffect(() => {
    if (storageKey) localStorage.setItem(storageKey, String(width))
  }, [width, storageKey])

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      dragRef.current = { startX: e.clientX, startW: width }

      const onMove = (ev: MouseEvent) => {
        if (!dragRef.current) return
        const delta = ev.clientX - dragRef.current.startX
        const next =
          direction === 'right'
            ? dragRef.current.startW + delta
            : dragRef.current.startW - delta
        setWidth(clampVal(next, minWidth, maxWidth))
      }

      const onUp = () => {
        dragRef.current = null
        window.removeEventListener('mousemove', onMove)
        window.removeEventListener('mouseup', onUp)
        document.body.style.cursor = ''
        document.body.style.userSelect = ''
      }

      document.body.style.cursor = 'col-resize'
      document.body.style.userSelect = 'none'
      window.addEventListener('mousemove', onMove)
      window.addEventListener('mouseup', onUp)
    },
    [width, minWidth, maxWidth, direction],
  )

  return { width, onMouseDown }
}
