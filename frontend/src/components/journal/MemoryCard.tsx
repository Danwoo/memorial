import type { DigestMemory, RelatedMemory } from '../../types'

type MemoryItem = DigestMemory | RelatedMemory

interface MemoryCardProps {
  memory: MemoryItem
  onInsert: (memory: MemoryItem) => void
}

export function MemoryCard({ memory, onInsert }: MemoryCardProps) {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('application/json', JSON.stringify(memory))
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div
      className="journal-memory-card"
      onClick={() => onInsert(memory)}
      draggable
      onDragStart={handleDragStart}
      title="클릭하여 에디터에 삽입"
    >
      <div className="journal-memory-card__type">{memory.type}</div>
      <div className="journal-memory-card__title">{memory.title}</div>
      <div className="journal-memory-card__summary">{memory.summary}</div>
    </div>
  )
}
