import { useState, useRef, useEffect } from 'react'

export function useBulkSelection(items: { id: string }[]) {
  const [selectMode, setSelectMode] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const lastSelectedIndexRef = useRef<number>(-1)

  const exitSelectMode = () => {
    setSelectMode(false)
    setSelectedIds(new Set())
    lastSelectedIndexRef.current = -1
  }

  const toggleSelectMode = () => {
    if (selectMode) exitSelectMode()
    else setSelectMode(true)
  }

  const toggleSelect = (id: string, index: number, shiftKey: boolean) => {
    setSelectedIds(prev => {
      const next = new Set(prev)
      if (shiftKey && lastSelectedIndexRef.current >= 0) {
        const start = Math.min(lastSelectedIndexRef.current, index)
        const end = Math.max(lastSelectedIndexRef.current, index)
        for (let i = start; i <= end; i++) {
          next.add(items[i].id)
        }
      } else {
        if (next.has(id)) next.delete(id)
        else next.add(id)
      }
      lastSelectedIndexRef.current = index
      return next
    })
  }

  const toggleSelectAll = () => {
    if (selectedIds.size === items.length) {
      setSelectedIds(new Set())
    } else {
      setSelectedIds(new Set(items.map(m => m.id)))
    }
  }

  // Escape 키로 선택 모드 해제
  useEffect(() => {
    if (!selectMode) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') exitSelectMode()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [selectMode])

  return {
    selectMode,
    selectedIds,
    exitSelectMode,
    toggleSelectMode,
    toggleSelect,
    toggleSelectAll,
  }
}
