import { Trash2, Tag } from 'lucide-react'

interface BulkActionBarProps {
  selectedCount: number
  loading: boolean
  onDelete: () => void
  onAddTags: () => void
  onRemoveTags: () => void
}

export default function BulkActionBar({
  selectedCount,
  loading,
  onDelete,
  onAddTags,
  onRemoveTags,
}: BulkActionBarProps) {
  return (
    <div className="bulk-action-bar">
      <span className="bulk-count">{selectedCount}개 선택</span>
      <button className="bulk-btn bulk-btn-danger" onClick={onDelete} disabled={loading}>
        <Trash2 size={16} /> 삭제
      </button>
      <button className="bulk-btn" onClick={onAddTags} disabled={loading}>
        <Tag size={16} /> 태그 추가
      </button>
      <button className="bulk-btn" onClick={onRemoveTags} disabled={loading}>
        <Tag size={16} /> 태그 제거
      </button>
    </div>
  )
}
