import { useState, useEffect, useRef, useCallback } from 'react'
import type { Editor } from '@tiptap/react'
import { Expand, Minimize2, Wand2 } from 'lucide-react'
import { useToast } from '../../contexts/ToastContext'
import type { InlineAIAction } from '../../types'
import { postInlineAssist, ApiResponseError } from '../../api'

// 버블 메뉴가 선택 영역 위에 표시될 때의 오프셋(px)
const MENU_OFFSET_TOP = 44

interface AIBubbleMenuProps {
  editor: Editor
}

const ACTIONS: { action: InlineAIAction; icon: typeof Expand; label: string }[] = [
  { action: 'expand', icon: Expand, label: '확장' },
  { action: 'summarize', icon: Minimize2, label: '요약' },
  { action: 'refine', icon: Wand2, label: '다듬기' },
]

export function AIBubbleMenu({ editor }: AIBubbleMenuProps) {
  const toast = useToast()
  const [isLoading, setIsLoading] = useState(false)
  const [show, setShow] = useState(false)
  const [position, setPosition] = useState({ top: 0, left: 0 })
  const menuRef = useRef<HTMLDivElement>(null)

  // blur 핸들러를 안정된 참조로 유지하여 cleanup 시 정확히 해제
  const handleBlur = useCallback(() => setShow(false), [])

  const updatePosition = useCallback(() => {
    const { from, to } = editor.state.selection
    if (from === to) {
      setShow(false)
      return
    }
    const domSelection = window.getSelection()
    if (!domSelection || domSelection.rangeCount === 0) {
      setShow(false)
      return
    }
    const range = domSelection.getRangeAt(0)
    const rect = range.getBoundingClientRect()
    if (rect.width === 0) {
      setShow(false)
      return
    }
    setPosition({
      top: rect.top - MENU_OFFSET_TOP,
      left: rect.left + rect.width / 2,
    })
    setShow(true)
  }, [editor])

  useEffect(() => {
    editor.on('selectionUpdate', updatePosition)
    editor.on('blur', handleBlur)
    return () => {
      editor.off('selectionUpdate', updatePosition)
      editor.off('blur', handleBlur)
    }
  }, [editor, updatePosition, handleBlur])

  const handleAction = async (action: InlineAIAction) => {
    const { from, to } = editor.state.selection
    const selectedText = editor.state.doc.textBetween(from, to, ' ')
    if (!selectedText.trim()) return

    setIsLoading(true)
    try {
      const { result } = await postInlineAssist(selectedText, action)
      editor.chain().focus().insertContentAt({ from, to }, result).run()
    } catch (err) {
      if (err instanceof ApiResponseError && err.status === 404) {
        toast.info('이 기능은 준비 중입니다.')
      } else {
        console.error('인라인 AI 처리 실패', err)
        toast.error('AI 처리 중 오류가 발생했습니다.')
      }
    } finally {
      setIsLoading(false)
      setShow(false)
    }
  }

  if (!show) return null

  return (
    <div
      ref={menuRef}
      className="ai-bubble-menu"
      style={{
        position: 'fixed',
        top: position.top,
        left: position.left,
        transform: 'translateX(-50%)',
        zIndex: 50,
      }}
    >
      {ACTIONS.map(({ action, icon: Icon, label }) => (
        <button
          key={action}
          className="ai-bubble-btn"
          onClick={() => handleAction(action)}
          disabled={isLoading}
          type="button"
          title={label}
        >
          <Icon size={14} />
          <span>{label}</span>
        </button>
      ))}
    </div>
  )
}
