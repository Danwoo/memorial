import type { ChatSessionResponse } from '../../types'

interface SessionPickerModalProps {
  sessions: ChatSessionResponse[]
  onSelect: (sessionId: string) => void
  onClose: () => void
}

export function SessionPickerModal({ sessions, onSelect, onClose }: SessionPickerModalProps) {
  return (
    <div className="session-picker-overlay" onClick={onClose}>
      <div className="session-picker" onClick={(e) => e.stopPropagation()}>
        <h3>대화 세션 선택</h3>
        <p className="session-picker-desc">저널로 정리할 대화를 선택하세요</p>
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
