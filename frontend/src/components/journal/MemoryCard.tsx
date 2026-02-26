import { Plus, Eye } from 'lucide-react'
import type { DigestScrap, RelatedScrap } from '../../types'

type ScrapItem = DigestScrap | RelatedScrap

interface ScrapCardProps {
  scrap: ScrapItem
  onInsert: (scrap: ScrapItem) => void
  onCardClick?: (scrapId: string) => void
}

export function MemoryCard({ scrap, onInsert, onCardClick }: ScrapCardProps) {
  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('application/json', JSON.stringify(scrap))
    e.dataTransfer.effectAllowed = 'copy'
  }

  return (
    <div
      className="journal-scrap-card"
      draggable
      onDragStart={handleDragStart}
    >
      <div className="journal-scrap-card__type">{scrap.type}</div>
      <div className="journal-scrap-card__title">{scrap.title}</div>
      <div className="journal-scrap-card__summary">{scrap.summary}</div>
      <div className="journal-scrap-card__actions">
        <button
          className="journal-scrap-card__action-btn journal-scrap-card__action-btn--insert"
          onClick={(e) => {
            e.stopPropagation()
            onInsert(scrap)
          }}
          title="에디터에 인용"
          type="button"
        >
          <Plus size={12} />
          <span>인용하기</span>
        </button>
        <button
          className="journal-scrap-card__action-btn journal-scrap-card__action-btn--detail"
          onClick={(e) => {
            e.stopPropagation()
            onCardClick?.(scrap.id)
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
