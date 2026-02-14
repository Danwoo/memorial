import { Plus } from 'lucide-react'
import type { DigestMemory, RelatedMemory } from '../../types'

type MemoryItem = DigestMemory | RelatedMemory

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
      onClick={() => onCardClick?.(memory.id)}
      draggable
      onDragStart={handleDragStart}
      title="클릭하여 상세 보기"
    >
      <div className="journal-memory-card__type">{memory.type}</div>
      <div className="journal-memory-card__title">{memory.title}</div>
      <div className="journal-memory-card__summary">{memory.summary}</div>
      <button
        className="journal-memory-card__insert-btn"
        onClick={(e) => {
          e.stopPropagation()
          onInsert(memory)
        }}
        title="에디터에 삽입"
        type="button"
      >
        <Plus size={14} />
      </button>
    </div>
  )
}
