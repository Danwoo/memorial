import { useState, useEffect } from 'react'
import { Globe, FileText, StickyNote, Upload } from 'lucide-react'
import { useFocusTrap } from '../../hooks/useFocusTrap'
import { useToast } from '../../contexts/ToastContext'
import type { MemoryCreatePayload, SourceType } from '../../types'
import { createMemory, uploadPdfMemory } from '../../api'

interface AddMemoryModalProps {
  onClose: () => void
  onAdded: () => void
}

export default function AddMemoryModal({ onClose, onAdded }: AddMemoryModalProps) {
  const toast = useToast()
  const trapRef = useFocusTrap(true)
  const [addType, setAddType] = useState<Extract<SourceType, 'WEB' | 'NOTE' | 'PDF'>>('WEB')
  const [newUrl, setNewUrl] = useState('')
  const [newNote, setNewNote] = useState('')
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [onClose])

  const addMemory = async () => {
    if (isSubmitting) return
    setIsSubmitting(true)
    try {
      if (addType === 'PDF') {
        if (!pdfFile) { setIsSubmitting(false); return }
        await uploadPdfMemory(pdfFile)
      } else {
        const payload: MemoryCreatePayload = addType === 'WEB'
          ? { sourceType: 'WEB', url: newUrl }
          : { sourceType: 'NOTE', content: newNote }
        await createMemory(payload)
      }
      onClose()
      onAdded()
      toast.success('메모리가 추가되었습니다!')
    } catch (error) {
      console.error('메모리 추가 실패:', error)
      toast.error('메모리 추가에 실패했습니다.')
      setIsSubmitting(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={onClose} ref={trapRef}>
      <div className="modal-content card" role="dialog" aria-modal="true" aria-label="새 메모리 추가" onClick={e => e.stopPropagation()}>
        <h2>새 메모리 추가</h2>

        <div className="modal-tabs">
          <button
            className={`tab ${addType === 'WEB' ? 'active' : ''}`}
            onClick={() => setAddType('WEB')}
          >
            <Globe size={16} /> 웹 URL
          </button>
          <button
            className={`tab ${addType === 'NOTE' ? 'active' : ''}`}
            onClick={() => setAddType('NOTE')}
          >
            <StickyNote size={16} /> 메모
          </button>
          <button
            className={`tab ${addType === 'PDF' ? 'active' : ''}`}
            onClick={() => setAddType('PDF')}
          >
            <FileText size={16} /> PDF
          </button>
        </div>

        {addType === 'WEB' ? (
          <input
            type="url"
            className="input"
            placeholder="https://example.com/article"
            value={newUrl}
            onChange={e => setNewUrl(e.target.value)}
          />
        ) : addType === 'NOTE' ? (
          <textarea
            className="input"
            placeholder="여기에 메모를 작성하세요..."
            value={newNote}
            onChange={e => setNewNote(e.target.value)}
            rows={5}
          />
        ) : (
          <div className="pdf-upload-area">
            <input
              type="file"
              accept=".pdf"
              id="pdf-input"
              onChange={e => setPdfFile(e.target.files?.[0] ?? null)}
            />
            <label htmlFor="pdf-input" className="pdf-drop-label">
              {pdfFile ? pdfFile.name : <><Upload size={16} /> PDF 파일을 선택하세요 (최대 20MB)</>}
            </label>
          </div>
        )}

        <div className="modal-actions">
          <button className="btn btn-secondary" onClick={onClose}>
            취소
          </button>
          <button className="btn btn-primary" onClick={addMemory} disabled={isSubmitting}>
            {isSubmitting ? '저장 중...' : '저장'}
          </button>
        </div>
      </div>
    </div>
  )
}
