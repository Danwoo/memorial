import { useState, useEffect } from 'react'
import { X, Loader2 } from 'lucide-react'
import './DuplicateModal.css'

interface DuplicateModalProps {
  onClose: () => void
  onMerged: () => void
}

export default function DuplicateModal({ onClose, onMerged: _onMerged }: DuplicateModalProps) {
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const timer = setTimeout(() => setLoading(false), 500)
    return () => clearTimeout(timer)
  }, [])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content duplicate-modal card" role="dialog" aria-modal="true" aria-label="중복 메모리 정리" onClick={e => e.stopPropagation()}>
        <div className="duplicate-modal-header">
          <h2>중복 메모리 정리</h2>
          <button className="btn btn-ghost" onClick={onClose}><X size={18} /></button>
        </div>
        {loading ? (
          <div className="duplicate-loading">
            <Loader2 size={24} className="spinning" />
            <p>중복 항목을 분석하고 있습니다...</p>
          </div>
        ) : (
          <div className="duplicate-empty">
            <p>중복 메모리가 없습니다.</p>
          </div>
        )}
      </div>
    </div>
  )
}
