import { useState, useEffect } from 'react'
import type { Memory, MemoryCreatePayload, SourceType } from '../types'
import { fetchMemories, createMemory, uploadPdfMemory } from '../api'
import './MemoryView.css'

export default function MemoryView() {
  const [memories, setMemories] = useState<Memory[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newUrl, setNewUrl] = useState('')
  const [newNote, setNewNote] = useState('')
  const [pdfFile, setPdfFile] = useState<File | null>(null)
  const [addType, setAddType] = useState<Extract<SourceType, 'WEB' | 'NOTE' | 'PDF'>>('WEB')

  const loadMemories = async () => {
    setIsLoading(true)
    try {
      const data = await fetchMemories()
      setMemories(data.items || [])
    } catch (error) {
      console.error('Failed to load memories:', error)
    } finally {
      setIsLoading(false)
    }
  }

  // 소스 타입에 따라 메모리 생성 (WEB/NOTE/PDF)
  const addMemory = async () => {
    try {
      if (addType === 'PDF') {
        if (!pdfFile) return
        await uploadPdfMemory(pdfFile)
      } else {
        const payload: MemoryCreatePayload = addType === 'WEB'
          ? { sourceType: 'WEB', url: newUrl }
          : { sourceType: 'NOTE', content: newNote }
        await createMemory(payload)
      }
      setShowAddModal(false)
      setNewUrl('')
      setNewNote('')
      setPdfFile(null)
      loadMemories()
    } catch (error) {
      console.error('Failed to add memory:', error)
    }
  }

  // 마운트 시 메모리 목록 로드
  useEffect(() => {
    loadMemories()
  }, [])

  return (
    <div className="memory-view">
      <div className="memory-header">
        <div>
          <h1>Memories</h1>
          <p className="memory-subtitle">저장된 지식을 탐색하세요</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowAddModal(true)}>
          + 추가
        </button>
      </div>

      <div className="memory-grid">
        {isLoading ? (
          <div className="loading-state">로딩 중...</div>
        ) : memories.length === 0 ? (
          <div className="empty-state">
            <div className="empty-icon">📦</div>
            <h3>아직 저장된 기억이 없습니다</h3>
            <p>웹 페이지나 메모를 추가해보세요</p>
          </div>
        ) : (
          memories.map(memory => (
            <div key={memory.id} className="memory-card glass-card">
              <div className="memory-type-badge">
                {memory.source_type === 'WEB' ? '🌐' : memory.source_type === 'PDF' ? '📄' : '📝'}
              </div>
              <h3 className="memory-title">{memory.title}</h3>
              {memory.summary && (
                <p className="memory-summary">{memory.summary}</p>
              )}
              <div className="memory-meta">
                <span>{new Date(memory.created_at).toLocaleDateString('ko-KR')}</span>
              </div>
            </div>
          ))
        )}
      </div>

      {/* 메모리 추가 모달 */}
      {showAddModal && (
        <div className="modal-overlay" onClick={() => setShowAddModal(false)}>
          <div className="modal-content glass-card" onClick={e => e.stopPropagation()}>
            <h2>새 메모리 추가</h2>
            
            <div className="modal-tabs">
              <button 
                className={`tab ${addType === 'WEB' ? 'active' : ''}`}
                onClick={() => setAddType('WEB')}
              >
                🌐 웹 URL
              </button>
              <button
                className={`tab ${addType === 'NOTE' ? 'active' : ''}`}
                onClick={() => setAddType('NOTE')}
              >
                📝 메모
              </button>
              <button
                className={`tab ${addType === 'PDF' ? 'active' : ''}`}
                onClick={() => setAddType('PDF')}
              >
                📄 PDF
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
                  {pdfFile ? pdfFile.name : '📄 PDF 파일을 선택하세요 (최대 20MB)'}
                </label>
              </div>
            )}

            <div className="modal-actions">
              <button className="btn btn-secondary" onClick={() => setShowAddModal(false)}>
                취소
              </button>
              <button className="btn btn-primary" onClick={addMemory}>
                저장
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
