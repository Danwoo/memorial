import { useState, useEffect, useCallback } from 'react'
import { X, ExternalLink, Trash2, Loader2, Globe, FileText, StickyNote, File, Tag } from 'lucide-react'
import { useToast } from '../contexts/ToastContext'
import type { MemoryDetail } from '../types'
import { fetchMemoryDetail, deleteMemory } from '../api'
import { formatDateKR } from '../utils'
import './MemoryDetailModal.css'

const SOURCE_LABELS: Record<string, string> = {
  WEB: '웹 페이지',
  PDF: 'PDF 문서',
  NOTE: '메모',
  KAKAO: '카카오톡',
  CHAT_HISTORY: '대화 기록',
  JOURNAL: '저널',
}

function SourceIcon({ type }: { type: string }) {
  switch (type) {
    case 'WEB': return <Globe size={16} />
    case 'PDF': return <FileText size={16} />
    case 'NOTE': return <StickyNote size={16} />
    default: return <File size={16} />
  }
}

interface MemoryDetailModalProps {
  memoryId: string
  onClose: () => void
  onDeleted: () => void
}

export default function MemoryDetailModal({ memoryId, onClose, onDeleted }: MemoryDetailModalProps) {
  const toast = useToast()
  const [detail, setDetail] = useState<MemoryDetail | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isDeleting, setIsDeleting] = useState(false)
  const [showConfirm, setShowConfirm] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  useEffect(() => {
    setIsLoading(true)
    fetchMemoryDetail(memoryId)
      .then(setDetail)
      .catch(() => {
        toast.error('메모리 상세 정보를 불러오지 못했습니다.')
        onClose()
      })
      .finally(() => setIsLoading(false))
  }, [memoryId, onClose, toast])

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

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="memory-detail-modal" onClick={e => e.stopPropagation()}>
        <div className="memory-detail-header">
          <h2>메모리 상세</h2>
          <button className="modal-close-btn" onClick={onClose} type="button">
            <X size={20} />
          </button>
        </div>

        {isLoading ? (
          <div className="memory-detail-loading">
            <Loader2 size={24} className="spin" />
            <span>불러오는 중...</span>
          </div>
        ) : detail ? (
          <div className="memory-detail-body">
            <h3 className="memory-detail-title">{detail.title}</h3>

            <div className="memory-detail-meta">
              <span className="memory-detail-source">
                <SourceIcon type={detail.source_type} />
                {SOURCE_LABELS[detail.source_type] ?? detail.source_type}
              </span>
              <span className="memory-detail-date">{formatDateKR(detail.created_at)}</span>
            </div>

            {detail.tags && detail.tags.length > 0 && (
              <div className="memory-detail-tags">
                <Tag size={14} />
                {detail.tags.map((tag, i) => (
                  <span key={i} className="memory-detail-tag">{tag}</span>
                ))}
              </div>
            )}

            {detail.source_url && (
              <a
                className="memory-detail-url"
                href={detail.source_url}
                target="_blank"
                rel="noopener noreferrer"
              >
                <ExternalLink size={14} />
                <span>{detail.source_url}</span>
              </a>
            )}

            {detail.summary && (
              <div className="memory-detail-section">
                <h4>요약</h4>
                <p>{detail.summary}</p>
              </div>
            )}

            <div className="memory-detail-section">
              <h4>내용</h4>
              <div className="memory-detail-content">{detail.content}</div>
            </div>

            <div className="memory-detail-actions">
              {showConfirm ? (
                <div className="memory-delete-confirm">
                  <span>정말 삭제하시겠습니까?</span>
                  <button
                    className="btn-confirm-delete"
                    onClick={handleDelete}
                    disabled={isDeleting}
                    type="button"
                  >
                    {isDeleting ? <Loader2 size={14} className="spin" /> : '삭제'}
                  </button>
                  <button
                    className="btn-cancel-delete"
                    onClick={() => setShowConfirm(false)}
                    disabled={isDeleting}
                    type="button"
                  >
                    취소
                  </button>
                </div>
              ) : (
                <button
                  className="btn-delete-memory"
                  onClick={() => setShowConfirm(true)}
                  type="button"
                >
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
