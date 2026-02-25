import { Plus, Eye } from 'lucide-react'
import type { DigestScrap, RelatedScrap } from '../../types'

type MemoryItem = DigestScrap | RelatedScrap

interface MemoryCardProps {
  memory: MemoryItem
  onInsert: (memory: MemoryItem) => void
  onCardClick?: (memoryId: string) => void
}

export function MemoryCard({ memory, onInsert, onCardClick }: MemoryCardProps) {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('application/json', JSON.stringify(memory))
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div
      className="journal-memory-card"
      draggable
      onDragStart={handleDragStart}
    >
      <div className="journal-memory-card__type">{memory.type}</div>
      <div className="journal-memory-card__title">{memory.title}</div>
      <div className="journal-memory-card__summary">{memory.summary}</div>
      <div className="journal-memory-card__actions">
        <button
          className="journal-memory-card__action-btn journal-memory-card__action-btn--insert"
          onClick={(e) => {
            e.stopPropagation()
            onInsert(memory)
          }}
          title="에디터에 인용"
          type="button"
        >
          <Plus size={12} />
          <span>인용하기</span>
        </button>
        <button
          className="journal-memory-card__action-btn journal-memory-card__action-btn--detail"
          onClick={(e) => {
            e.stopPropagation()
            onCardClick?.(memory.id)
          }}
          title="상세 보기"
          type="button"
        >
          <Eye size={12} />
          <span>상세 보기</span>
        </button>
      </div>
    </div>
  )
}
