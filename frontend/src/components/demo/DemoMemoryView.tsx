import { useState } from 'react'
import { BookOpen, Globe, FileText, StickyNote, Search } from 'lucide-react'
import { DEMO_MEMORIES, DEMO_MEMORY_DETAILS } from '../../data/demo-data'
import { useToast } from '../../contexts/ToastContext'
import '../MemoryView.css'

const SOURCE_ICONS: Record<string, typeof Globe> = { WEB: Globe, PDF: FileText, NOTE: StickyNote }

export default function DemoMemoryView() {
  const toast = useToast()
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [searchQuery, setSearchQuery] = useState('')

  const filtered = searchQuery
    ? DEMO_MEMORIES.filter(m =>
        m.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.summary?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        m.tags?.some(t => t.toLowerCase().includes(searchQuery.toLowerCase()))
      )
    : DEMO_MEMORIES

  const detail = selectedId ? DEMO_MEMORY_DETAILS[selectedId] : null

  const handleWriteAction = () => {
    toast.info('데모 모드에서는 수정할 수 없습니다. 회원가입 후 이용해주세요!')
  }

  return (
    <div className="memory-view">
      <div className="memory-header">
        <h1><BookOpen size={24} /> 기억 저장소</h1>
        <div className="memory-header-actions">
          <button className="btn btn-primary" onClick={handleWriteAction}>+ 기억 추가</button>
        </div>
      </div>

      {/* 필터 바 */}
      <div className="filter-bar">
        <div className="filter-bar-chips">
          <span className="filter-chip active">전체</span>
          <span className="filter-chip" onClick={handleWriteAction}>WEB</span>
          <span className="filter-chip" onClick={handleWriteAction}>PDF</span>
          <span className="filter-chip" onClick={handleWriteAction}>NOTE</span>
        </div>
      </div>

      {/* 검색 */}
      <div className="memory-search-box" style={{ marginBottom: 16 }}>
        <Search size={16} />
        <input
          type="text"
          placeholder="메모리 검색..."
          value={searchQuery}
          onChange={e => setSearchQuery(e.target.value)}
          className="memory-search-input"
        />
      </div>

      {/* 그리드 */}
      <div className="memory-grid">
        {filtered.map(m => {
          const Icon = SOURCE_ICONS[m.source_type] || Globe
          return (
            <div key={m.id} className="memory-card" onClick={() => setSelectedId(m.id)}>
              <div className="memory-card-header">
                <span className={`source-chip source-${m.source_type.toLowerCase()}`}>
                  <Icon size={12} /> {m.source_type}
                </span>
                <span className="memory-date">{new Date(m.created_at).toLocaleDateString('ko-KR')}</span>
              </div>
              <h3 className="memory-card-title">{m.title}</h3>
              {m.summary && <p className="memory-card-summary">{m.summary}</p>}
              {m.tags && m.tags.length > 0 && (
                <div className="memory-card-tags">
                  {m.tags.map(t => <span key={t} className="memory-tag">{t}</span>)}
                </div>
              )}
            </div>
          )
        })}
      </div>

      {/* 상세 모달 */}
      {selectedId && (
        <div className="modal-overlay" onClick={() => setSelectedId(null)}>
          <div className="memory-detail-modal" onClick={e => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setSelectedId(null)}>×</button>
            {detail ? (
              <>
                <h2>{detail.title}</h2>
                <p>{detail.summary}</p>
                <div className="memory-card-tags" style={{ marginTop: 12 }}>
                  {detail.tags?.map(t => <span key={t} className="memory-tag">{t}</span>)}
                </div>
              </>
            ) : (
              <>
                <h2>{DEMO_MEMORIES.find(m => m.id === selectedId)?.title}</h2>
                <p>{DEMO_MEMORIES.find(m => m.id === selectedId)?.summary}</p>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
