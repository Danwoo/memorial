import { useState, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ChatView from './ChatView'
import './JournalView.css'

interface RelatedMemory {
  id: string
  title: string
  summary: string
  type: string
  created_at: string
  similarity: number
}

export default function JournalView() {
  const [content, setContent] = useState('# 2024년 2월 7일 회고\n\n오늘은...\n\n')
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [isSaving, setIsSaving] = useState(false)
  const [relatedMemories, setRelatedMemories] = useState<RelatedMemory[]>([])
  const [isLoadingContext, setIsLoadingContext] = useState(false)

  // Debounced fetch for related memories
  const fetchRelatedMemories = useCallback(async (text: string) => {
    if (!text || text.trim().length < 20) {
      setRelatedMemories([])
      return
    }
    setIsLoadingContext(true)
    try {
      const res = await fetch('/api/v1/journals/related-memories', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ content: text })
      })
      if (res.ok) {
        const data = await res.json()
        setRelatedMemories(data.memories || [])
      }
    } catch (e) {
      console.error('Failed to fetch related memories', e)
    } finally {
      setIsLoadingContext(false)
    }
  }, [])

  // Debounce content changes
  useEffect(() => {
    const timer = setTimeout(() => {
      fetchRelatedMemories(content)
    }, 1500) // 1.5초 후 검색
    return () => clearTimeout(timer)
  }, [content, fetchRelatedMemories])

  const handleSave = async () => {
    if (!content.trim()) return
    setIsSaving(true)
    try {
        const res = await fetch('/api/v1/journals', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content })
        })
        if (res.ok) {
            alert('저장되었습니다!')
        } else {
            console.error('Failed to save')
            alert('저장 실패')
        }
    } catch (e) {
        console.error(e)
        alert('에러 발생')
    } finally {
        setIsSaving(false)
    }
  }
  
  return (
    <div className="journal-view">
      <div className="editor-section">
        <div className="editor-header">
            <h2>Today's Journal</h2>
            <div className="editor-actions">
                <button 
                    className="save-btn" 
                    onClick={handleSave}
                    disabled={isSaving}
                >
                    {isSaving ? 'Saving...' : 'Save Draft'}
                </button>
            </div>
        </div>
        <div className="editor-container">
            <textarea
                className="markdown-input"
                value={content}
                onChange={(e) => setContent(e.target.value)}
                placeholder="오늘 하루는 어떠셨나요? 자유롭게 기록해보세요..."
            />
            <div className="markdown-preview">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
            </div>
        </div>
      </div>
      
      {/* Context Sidebar */}
      <div className="context-sidebar">
        <div className="context-header">
          <h3>📚 Related Memories</h3>
          {isLoadingContext && <span className="loading-indicator">...</span>}
        </div>
        <div className="context-list">
          {relatedMemories.length > 0 ? (
            relatedMemories.map(memory => (
              <div key={memory.id} className="memory-card">
                <div className="memory-type">{memory.type}</div>
                <div className="memory-title">{memory.title}</div>
                <div className="memory-summary">{memory.summary}</div>
              </div>
            ))
          ) : (
            <div className="no-context">
              글을 작성하시면 연관된 메모가 여기에 표시됩니다.
            </div>
          )}
        </div>
      </div>
      
      <div className="companion-section">
        <div className="companion-header">
            <h3>Thinking Partner</h3>
        </div>
        <div className="chat-wrapper">
             <ChatView 
                sessionId={sessionId} 
                onSessionCreate={setSessionId} 
             />
        </div>
      </div>
    </div>
  )
}

