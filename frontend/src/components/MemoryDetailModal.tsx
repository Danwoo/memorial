import { useState, useEffect, useCallback, useRef } from 'react'
import { X, ExternalLink, Trash2, Loader2, Tag, Pencil, Save, Undo2, BookOpen, PenLine, Network, MessageSquare } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useToast } from '../contexts/ToastContext'
import { useFocusTrap } from '../hooks/useFocusTrap'
import type { MemoryDetail, RelatedMemory, LinkedJournal } from '../types'
import { fetchMemoryDetail, deleteMemory, updateMemory, fetchUserTags, fetchRelatedMemoriesById, fetchMemoryJournals } from '../api'
import { formatDateKR } from '../utils'
import SourceIcon from './shared/SourceIcon'
import './MemoryDetailModal.css'

const SOURCE_LABELS: Record<string, string> = {
  WEB: '웹 페이지',
  PDF: 'PDF 문서',
  NOTE: '메모',
  KAKAO: '카카오톡',
  CHAT_HISTORY: '대화 기록',
  JOURNAL: '저널',
}

interface MemoryDetailModalProps {
  memoryId: string
  onClose: () => void
  onDeleted: () => void
  onUpdated?: () => void
}

export default function MemoryDetailModal({ memoryId, onClose, onDeleted, onUpdated }: MemoryDetailModalProps) {
  const toast = useToast()
  const navigate = useNavigate()
  const trapRef = useFocusTrap()
  const onCloseRef = useRef(onClose)
  onCloseRef.current = onClose
  const [detail, setDetail] = useState<MemoryDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)
  const [relatedMemories, setRelatedMemories] = useState<RelatedMemory[]>([])
  const [isLoadingRelated, setIsLoadingRelated] = useState(false)
  const [relatedFailed, setRelatedFailed] = useState(false)
  const [linkedJournals, setLinkedJournals] = useState<LinkedJournal[]>([])
  const [isLoadingJournals, setIsLoadingJournals] = useState(false)

  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editSummary, setEditSummary] = useState('')
  const [editTags, setEditTags] = useState<string[]>([])
  const [newTagInput, setNewTagInput] = useState('')
  const [tagSuggestions, setTagSuggestions] = useState<string[]>([])
  const [showSuggestions, setShowSuggestions] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const tagInputRef = useRef<HTMLInputElement>(null)
  const suggestionsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        if (isEditing) {
          setIsEditing(false)
        } else {
          onClose()
        }
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose, isEditing])

  useEffect(() => {
    setIsLoading(true)
    fetchMemoryDetail(memoryId)
      .then(data => {
        setDetail(data)
        setIsLoadingRelated(true)
        setRelatedFailed(false)
        const relatedTimeout = new Promise<never>((_, reject) =>
          setTimeout(() => reject(new Error('timeout')), 10_000)
        )
        Promise.race([fetchRelatedMemoriesById(memoryId), relatedTimeout])
          .then(setRelatedMemories)
          .catch(() => setRelatedFailed(true))
          .finally(() => setIsLoadingRelated(false))
        setIsLoadingJournals(true)
        fetchMemoryJournals(memoryId)
          .then(res => setLinkedJournals(res.journals))
          .catch(() => {})
          .finally(() => setIsLoadingJournals(false))
      })
      .catch(() => {
        toast.error('메모리 상세 정보를 불러오지 못했습니다.')
        onCloseRef.current()
      })
      .finally(() => setIsLoading(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [memoryId])

  const enterEditMode = useCallback(() => {
    if (!detail) return
    setEditTitle(detail.title)
    setEditSummary(detail.summary ?? '')
    setEditTags(detail.tags ?? [])
    setNewTagInput('')
    setIsEditing(true)
  }, [detail])

  const handleSave = useCallback(async () => {
    if (!detail) return
    setIsSaving(true)
    try {
      const body: { title?: string; summary?: string; tags?: string[] } = {}
      if (editTitle !== detail.title) body.title = editTitle
      if (editSummary !== (detail.summary ?? '')) body.summary = editSummary
      if (JSON.stringify(editTags) !== JSON.stringify(detail.tags ?? [])) body.tags = editTags

      if (Object.keys(body).length === 0) {
        setIsEditing(false)
        return
      }

      const updated = await updateMemory(memoryId, body)
      setDetail(updated)
      setIsEditing(false)
      toast.success('메모리가 수정되었습니다.')
      onUpdated?.()
    } catch {
      toast.error('메모리 수정에 실패했습니다.')
    } finally {
      setIsSaving(false)
    }
  }, [detail, editTitle, editSummary, editTags, memoryId, toast, onUpdated])

  const handleDelete = useCallback(async () => {
    setIsDeleting(true)
    try {
      await deleteMemory(memoryId)
      toast.success('메모리가 삭제되었습니다.')
      onDeleted()
    } catch {
      toast.error('메모리 삭제에 실패했습니다.')
    } finally {
      setIsDeleting(false)
      setShowConfirm(false)
    }
  }, [memoryId, toast, onDeleted])

  const removeTag = (index: number) => {
    setEditTags(prev => prev.filter((_, i) => i !== index))
  }

  const addTag = (tag: string) => {
    const trimmed = tag.trim()
    if (trimmed && !editTags.includes(trimmed)) {
      setEditTags(prev => [...prev, trimmed])
    }
    setNewTagInput('')
    setShowSuggestions(false)
    tagInputRef.current?.focus()
  }

  const handleTagInputChange = async (value: string) => {
    setNewTagInput(value)
    if (value.length >= 1) {
      try {
        const suggestions = await fetchUserTags(value)
        setTagSuggestions(suggestions.filter(s => !editTags.includes(s)))
        setShowSuggestions(true)
      } catch {
        setTagSuggestions([])
      }
    } else {
      setShowSuggestions(false)
    }
  }

  const handleTagKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' || e.key === ',') {
      e.preventDefault()
      if (newTagInput.trim()) addTag(newTagInput)
    } else if (e.key === 'Backspace' && !newTagInput && editTags.length > 0) {
      setEditTags(prev => prev.slice(0, -1))
    }
  }

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (suggestionsRef.current && !suggestionsRef.current.contains(e.target as Node)) {
        setShowSuggestions(false)
      }
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  return (
    <div className="modal-overlay" onClick={onClose} ref={trapRef}>
      <div className="memory-detail-modal" role="dialog" aria-modal="true" aria-label="메모리 상세" onClick={e => e.stopPropagation()}>
        <div className="memory-detail-header">
          <h2>{isEditing ? '메모리 편집' : '메모리 상세'}</h2>
          <div className="memory-detail-header-actions">
            {!isEditing && detail && (
              <button className="btn-edit-memory" onClick={enterEditMode} type="button" title="편집">
                <Pencil size={16} />
              </button>
            )}
            <button className="modal-close-btn" onClick={onClose} type="button">
              <X size={20} />
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="memory-detail-loading">
            <Loader2 size={24} className="spin" />
            <span>불러오는 중...</span>
          </div>
        ) : detail ? (
          <div className="memory-detail-body">
            {isEditing ? (
              <input
                className="edit-title-input"
                value={editTitle}
                onChange={e => setEditTitle(e.target.value)}
                placeholder="제목"
                autoFocus
              />
            ) : (
              <h3 className="memory-detail-title">{detail.title}</h3>
            )}

            <div className="memory-detail-meta">
              <span className="memory-detail-source">
                <SourceIcon type={detail.source_type} />
                {SOURCE_LABELS[detail.source_type] ?? detail.source_type}
              </span>
              <span className="memory-detail-date">{formatDateKR(detail.created_at)}</span>
            </div>

            {isEditing ? (
              <div className="edit-tags-section">
                <div className="edit-tags-list">
                  {editTags.map((tag, i) => (
                    <span key={i} className="edit-tag-chip">
                      {tag}
                      <button type="button" className="edit-tag-remove" onClick={() => removeTag(i)}>×</button>
                    </span>
                  ))}
                  <div className="tag-input-wrapper" ref={suggestionsRef}>
                    <input
                      ref={tagInputRef}
                      className="edit-tag-input"
                      value={newTagInput}
                      onChange={e => handleTagInputChange(e.target.value)}
                      onKeyDown={handleTagKeyDown}
                      placeholder="태그 추가..."
                    />
                    {showSuggestions && tagSuggestions.length > 0 && (
                      <div className="tag-suggestions">
                        {tagSuggestions.slice(0, 8).map(s => (
                          <button key={s} type="button" className="tag-suggestion-item" onClick={() => addTag(s)}>
                            {s}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                </div>
              </div>
            ) : detail.tags && detail.tags.length > 0 ? (
              <div className="memory-detail-tags">
                <Tag size={14} />
                {detail.tags.map((tag, i) => (
                  <span key={i} className="memory-detail-tag">{tag}</span>
                ))}
              </div>
            ) : null}

            {detail.source_url && (
              <a className="memory-detail-url" href={detail.source_url} target="_blank" rel="noopener noreferrer">
                <ExternalLink size={14} />
                <span>{detail.source_url}</span>
              </a>
            )}

            {isEditing ? (
              <div className="memory-detail-section">
                <h4>요약</h4>
                <textarea
                  className="edit-summary-textarea"
                  value={editSummary}
                  onChange={e => setEditSummary(e.target.value)}
                  placeholder="요약을 입력하세요"
                  rows={3}
                />
              </div>
            ) : detail.summary ? (
              <div className="memory-detail-section">
                <h4>요약</h4>
                <p>{detail.summary}</p>
              </div>
            ) : null}

            {!isEditing && (
              <div className="memory-detail-section">
                <h4>내용</h4>
                <div className="memory-detail-content">{detail.content}</div>
              </div>
            )}

            {!isEditing && (
              <div className="memory-detail-section">
                <h4>관련 메모리</h4>
                {isLoadingRelated ? (
                  <div className="related-loading">
                    <Loader2 size={16} className="spin" />
                    <span>찾는 중...</span>
                  </div>
                ) : relatedMemories.length > 0 ? (
                  <div className="related-list">
                    {relatedMemories.map(related => (
                      <div key={related.id} className="related-item">
                        <div className="related-title">{related.title}</div>
                        {related.summary && (
                          <div className="related-summary">{related.summary}</div>
                        )}
                        <div className="related-meta">
                          <span className="related-similarity">
                            {Math.round(related.similarity * 100)}% 유사
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="related-empty">
                    {relatedFailed ? '관련 기억을 찾지 못했습니다.' : '아직 연결된 기억이 없습니다.'}
                  </p>
                )}
              </div>
            )}

            {!isEditing && (
              <div className="memory-detail-section">
                <h4>관련 저널</h4>
                {isLoadingJournals ? (
                  <div className="related-loading">
                    <Loader2 size={16} className="spin" />
                    <span>찾는 중...</span>
                  </div>
                ) : linkedJournals.length > 0 ? (
                  <div className="linked-journals-list">
                    {linkedJournals.map(journal => (
                      <button
                        key={journal.journal_id}
                        className="linked-journal-item"
                        onClick={() => {
                          onClose()
                          navigate(`/journal`, { state: { date: journal.date } })
                        }}
                        type="button"
                      >
                        <BookOpen size={14} className="linked-journal-icon" />
                        <div className="linked-journal-content">
                          <span className="linked-journal-date">{formatDateKR(journal.date)}</span>
                          <span className="linked-journal-preview">{journal.preview}</span>
                        </div>
                        {journal.mood && (
                          <span className="linked-journal-mood">
                            {journal.mood === 'POSITIVE' ? '😊' : journal.mood === 'NEGATIVE' ? '😔' : '📝'}
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="linked-journals-empty">
                    <p>아직 이 기억에 대해 작성한 저널이 없습니다.</p>
                    <button
                      className="linked-journals-cta"
                      onClick={() => {
                        onClose()
                        navigate('/journal')
                      }}
                      type="button"
                    >
                      <PenLine size={14} />
                      이 기억에 대해 저널을 써보세요
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* 크로스 네비게이션 */}
            {!isEditing && (
              <div className="memory-detail-cross-nav">
                <button
                  className="btn-cross-nav"
                  onClick={() => {
                    onClose()
                    navigate('/graph', { state: { focusNodeId: memoryId } })
                  }}
                  type="button"
                >
                  <Network size={14} />
                  그래프에서 보기
                </button>
                <button
                  className="btn-cross-nav"
                  onClick={() => {
                    onClose()
                    navigate('/chat', { state: { topic: detail.title } })
                  }}
                  type="button"
                >
                  <MessageSquare size={14} />
                  이 주제로 대화하기
                </button>
              </div>
            )}

            <div className="memory-detail-actions">
              {isEditing ? (
                <div className="edit-actions">
                  <button className="btn-save-memory" onClick={handleSave} disabled={isSaving || !editTitle.trim()} type="button">
                    {isSaving ? <Loader2 size={14} className="spin" /> : <Save size={14} />}
                    <span>저장</span>
                  </button>
                  <button className="btn-cancel-edit" onClick={() => setIsEditing(false)} disabled={isSaving} type="button">
                    <Undo2 size={14} />
                    <span>취소</span>
                  </button>
                </div>
              ) : showConfirm ? (
                <div className="memory-delete-confirm">
                  <span>정말 삭제하시겠습니까?</span>
                  <button className="btn-confirm-delete" onClick={handleDelete} disabled={isDeleting} type="button">
                    {isDeleting ? <Loader2 size={14} className="spin" /> : '삭제'}
                  </button>
                  <button className="btn-cancel-delete" onClick={() => setShowConfirm(false)} disabled={isDeleting} type="button">
                    취소
                  </button>
                </div>
              ) : (
                <button className="btn-delete-memory" onClick={() => setShowConfirm(true)} type="button">
                  <Trash2 size={14} />
                  <span>삭제</span>
                </button>
              )}
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
