import { useState } from 'react'
import './MemoryView.css'

interface Memory {
  id: string
  title: string
  summary: string | null
  source_type: 'WEB' | 'PDF' | 'NOTE'
  created_at: string
}

const API_BASE = '/api/v1'

export default function MemoryView() {
  const [memories, setMemories] = useState<Memory[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [showAddModal, setShowAddModal] = useState(false)
  const [newUrl, setNewUrl] = useState('')
  const [newNote, setNewNote] = useState('')
  const [addType, setAddType] = useState<'WEB' | 'NOTE'>('WEB')

  const loadMemories = async () => {
    setIsLoading(true)
    try {
      const res = await fetch(`${API_BASE}/memories`)
      const data = await res.json()
      setMemories(data.items || [])
    } catch (error) {
      console.error('Failed to load memories:', error)
    } finally {
      setIsLoading(false)
    }
  }

  const addMemory = async () => {
    try {
      const body = addType === 'WEB' 
        ? { sourceType: 'WEB', url: newUrl }
        : { sourceType: 'NOTE', content: newNote }

      const res = await fetch(`${API_BASE}/memories`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
      })

      if (res.ok) {
        setShowAddModal(false)
        setNewUrl('')
        setNewNote('')
        loadMemories()
      }
    } catch (error) {
      console.error('Failed to add memory:', error)
    }
  }

  // Load on mount
  useState(() => {
    loadMemories()
  })

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

      {/* Add Memory Modal */}
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
            </div>

            {addType === 'WEB' ? (
              <input
                type="url"
                className="input"
                placeholder="https://example.com/article"
                value={newUrl}
                onChange={e => setNewUrl(e.target.value)}
              />
            ) : (
              <textarea
                className="input"
                placeholder="여기에 메모를 작성하세요..."
                value={newNote}
                onChange={e => setNewNote(e.target.value)}
                rows={5}
              />
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
