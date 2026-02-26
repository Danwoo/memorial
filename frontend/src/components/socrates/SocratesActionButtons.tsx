import { useState } from 'react'
import { Paperclip, PenLine, Check } from 'lucide-react'

interface SocratesActionButtonsProps {
  content: string
  onSaveAsScrap?: (content: string) => void
  onInsertToDiary?: (content: string) => void
  isPanelMode: boolean
}

export default function SocratesActionButtons({
  content,
  onSaveAsScrap,
  onInsertToDiary,
  isPanelMode,
}: SocratesActionButtonsProps) {
  const [savedAsScrap, setSavedAsScrap] = useState(false)
  const [insertedToDiary, setInsertedToDiary] = useState(false)

  return (
    <div className="socrates-action-buttons">
      {onSaveAsScrap && (
        <button
          type="button"
          className={`socrates-action-btn${savedAsScrap ? ' socrates-action-btn--done' : ''}`}
          onClick={() => {
            onSaveAsScrap(content)
            setSavedAsScrap(true)
          }}
          disabled={savedAsScrap}
        >
          {savedAsScrap ? <Check size={12} /> : <Paperclip size={12} />}
          {savedAsScrap ? '저장됨' : '스크랩으로 저장'}
        </button>
      )}
      {isPanelMode && onInsertToDiary && (
        <button
          type="button"
          className={`socrates-action-btn${insertedToDiary ? ' socrates-action-btn--done' : ''}`}
          onClick={() => {
            onInsertToDiary(content)
            setInsertedToDiary(true)
          }}
          disabled={insertedToDiary}
        >
          {insertedToDiary ? <Check size={12} /> : <PenLine size={12} />}
          {insertedToDiary ? '삽입됨' : '일기에 삽입'}
        </button>
      )}
    </div>
  )
}
