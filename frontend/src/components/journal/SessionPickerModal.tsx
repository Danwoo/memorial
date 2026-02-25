import { useEffect } from 'react'
import type { SocratesSessionResponse } from '../../types'
import { useFocusTrap } from '../../hooks/useFocusTrap'

interface SessionPickerModalProps {
  sessions: SocratesSessionResponse[]
  onSelect: (sessionId: string) => void
  onClose: () => void
}

export function SessionPickerModal({ sessions, onSelect, onClose }: SessionPickerModalProps) {
  const trapRef = useFocusTrap()

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  return (
    <div className="session-picker-overlay" onClick={onClose} ref={trapRef}>
      <div className="session-picker" role="dialog" aria-modal="true" aria-label="세션 선택" onClick={(e) => e.stopPropagation()}>
        <h3>대화 세션 선택</h3>
        <p className="session-picker-desc">다이어리로 정리할 대화를 선택하세요</p>
        <div className="session-list">
          {sessions.map((session) => (
            <button
              key={session.id}
              className="session-item"
              onClick={() => onSelect(session.id)}
              type="button"
            >
              <span className="session-title">{session.title}</span>
              <span className="session-date">
                {new Date(session.created_at).toLocaleDateString('ko-KR')}
              </span>
            </button>
          ))}
        </div>
        <button className="session-cancel" onClick={onClose} type="button">
          취소
        </button>
      </div>
    </div>
  )
}
