import { ArrowUp } from 'lucide-react'

interface SocratesInputBarProps {
  input: string
  isLoading: boolean
  textareaRef: React.RefObject<HTMLTextAreaElement>
  onInputChange: (value: string) => void
  onSend: () => void
  onKeyDown: (e: React.KeyboardEvent) => void
  onAdjustHeight: () => void
}

export default function SocratesInputBar({
  input, isLoading, textareaRef,
  onInputChange, onSend, onKeyDown, onAdjustHeight,
}: SocratesInputBarProps) {
  return (
    <div className="socrates-input-container">
      <div className="socrates-input-wrapper">
        <textarea
          ref={textareaRef}
          className="socrates-input"
          placeholder="메시지를 입력하세요..."
          value={input}
          onChange={(e) => {
            onInputChange(e.target.value)
            onAdjustHeight()
          }}
          onKeyDown={onKeyDown}
          rows={1}
          disabled={isLoading}
        />
        <button
          className="send-button"
          onClick={onSend}
          disabled={!input.trim() || isLoading}
        >
          {isLoading ? <div className="loading-spinner small" /> : <ArrowUp size={18} />}
        </button>
      </div>
    </div>
  )
}
