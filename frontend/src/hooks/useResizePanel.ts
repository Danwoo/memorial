import { useState, useRef, useCallback, useEffect } from 'react'

function clampVal(val: number, min: number, max: number) {
  return Math.max(min, Math.min(max, val))
}

/**
 * 패널 드래그 리사이즈 훅.
 * 너비를 vw(viewport width %) 단위로 관리해 모든 화면 크기에서 비례 유지.
 * direction: 'right' = 핸들이 오른쪽 → 마우스 오른쪽 이동 시 패널 확장
 *            'left'  = 핸들이 왼쪽  → 마우스 왼쪽  이동 시 패널 확장
 * storageKey: localStorage 키 (제공 시 vw 값 저장/복원)
 */
export function useResizePanel(
  defaultVw: number,
  minVw: number,
  maxVw: number,
  direction: 'left' | 'right' = 'right',
  storageKey?: string,
) {
  const [vw, setVw] = useState<number>(() => {
    if (storageKey) {
      const stored = localStorage.getItem(storageKey)
      if (stored) return clampVal(Number(stored), minVw, maxVw)
    }
    return defaultVw
  })

  const dragRef = useRef<{ startX: number; startVw: number } | null>(null)

  useEffect(() => {
    if (storageKey) localStorage.setItem(storageKey, String(vw))
  }, [vw, storageKey])

  const onMouseDown = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault()
      dragRef.current = { startX: e.clientX, startVw: vw }

      const onMove = (ev: MouseEvent) => {
        if (!dragRef.current) return
        const deltaPx = ev.clientX - dragRef.current.startX
        const deltaVw = (deltaPx / window.innerWidth) * 100
        const next =
          direction === 'right'
            ? dragRef.current.startVw + deltaVw
            : dragRef.current.startVw - deltaVw
        setVw(clampVal(next, minVw, maxVw))
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
    [vw, minVw, maxVw, direction],
  )

  return { vw, onMouseDown }
}
