import { useEffect, useRef } from 'react'

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'button:not([disabled])',
  'textarea:not([disabled])',
  'input:not([disabled])',
  'select:not([disabled])',
  '[tabindex]:not([tabindex="-1"])',
].join(', ')

/**
 * 모달/다이얼로그용 포커스 트랩 훅.
 * Tab/Shift+Tab 순환, 배경 스크롤 방지, 닫힐 때 포커스 복원.
 */
export function useFocusTrap(active: boolean = true) {
  const containerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!active) return

    const container = containerRef.current
    if (!container) return

    // 배경 스크롤 방지
    const prevOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'

    // 이전 포커스 저장 후 첫 포커스 가능 요소로 이동
    const previouslyFocused = document.activeElement as HTMLElement | null
    const focusFirst = () => {
      const elements = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      elements[0]?.focus()
    }
    requestAnimationFrame(focusFirst)

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return

      const focusable = container.querySelectorAll<HTMLElement>(FOCUSABLE_SELECTOR)
      if (focusable.length === 0) return

      const first = focusable[0]
      const last = focusable[focusable.length - 1]

      if (e.shiftKey) {
        if (document.activeElement === first) {
          e.preventDefault()
          last.focus()
        }
      } else {
        if (document.activeElement === last) {
          e.preventDefault()
          first.focus()
        }
      }
    }

    container.addEventListener('keydown', handleKeyDown)

    return () => {
      container.removeEventListener('keydown', handleKeyDown)
      document.body.style.overflow = prevOverflow
      previouslyFocused?.focus()
    }
  }, [active])

  return containerRef
}
