import { useState, useRef } from 'react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useToast } from '../../contexts/ToastContext'
import { bulkScrapAction, fetchUserTags } from '../../api'

interface BulkTagModalProps {
  action: 'add_tags' | 'remove_tags'
  selectedIds: Set<string>
  onClose: () => void
  onDone: () => void
}

export default function BulkTagModal({ action, selectedIds, onClose, onDone }: BulkTagModalProps) {
  const toast = useToast()
  const trapRef = useFocusTrap(true)
  const tagInputRef = useRef<HTMLInputElement>(null)
  const [tagInput, setTagInput] = useState('')
  const [suggestions, setSuggestions] = useState<string[]>([])
  const [loading, setLoading] = useState(false)

  const handleTagInputChange = async (value: string) => {
    setTagInput(value)
    if (value.length >= 1) {
      try {
        const tags = await fetchUserTags(value)
        setSuggestions(tags.slice(0, 5))
      } catch {
        setSuggestions([])
      }
    } else {
      setSuggestions([])
    }
  }

  const handleSubmit = async () => {
    const tag = (tagInput || tagInputRef.current?.value || '').trim()
    if (!tag || selectedIds.size === 0) return

    setLoading(true)
    try {
      const result = await bulkScrapAction({
        action,
        scrap_ids: Array.from(selectedIds),
        tags: [tag],
      })
      const actionLabel = action === 'add_tags' ? '추가' : '제거'
      toast.success(`${result.affected}개 스크랩에 태그를 ${actionLabel}했습니다`)
      onDone()
    } catch {
      toast.error('태그 작업에 실패했습니다')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose} ref={trapRef}>
      <div className="modal-content card" role="dialog" aria-modal="true" aria-label="태그 일괄 작업" onClick={e => e.stopPropagation()}>
        <h2>{action === 'add_tags' ? '태그 추가' : '태그 제거'}</h2>
        <p className="tag-modal-desc">
          {selectedIds.size}개 스크랩에 태그를 {action === 'add_tags' ? '추가' : '제거'}합니다
        </p>
        <div className="tag-modal-input-wrapper">
          <input
            ref={tagInputRef}
            type="text"
            className="input"
            placeholder="태그 입력..."
            value={tagInput}
            onChange={e => handleTagInputChange(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSubmit() }}
            autoFocus
          />
          {suggestions.length > 0 && (
            <div className="tag-modal-suggestions">
              {suggestions.map(s => (
                <button key={s} className="tag-suggestion-item" onClick={() => setTagInput(s)}>
                  #{s}
                </button>
              ))}
            </div>
          )}
        </div>
        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>취소</button>
          <button className="btn btn-primary" onClick={handleSubmit} disabled={!tagInput.trim() || loading}>
            {loading ? '처리 중...' : '적용'}
          </button>
        </div>
      </div>
    </div>
  )
}
