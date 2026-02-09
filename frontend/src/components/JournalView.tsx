import { useState, useEffect, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import ChatView from './ChatView'
import type { RelatedMemory, ChatSessionResponse } from '../types'
import { saveJournal, fetchRelatedMemories as fetchRelatedMemoriesApi, generateJournalDraft, fetchChatSessions } from '../api'
import './JournalView.css'

export default function JournalView() {
  const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
  const [content, setContent] = useState(`# ${today} 회고\n\n오늘은...\n\n`)
  const [isSaving, setIsSaving] = useState(false)
  const [relatedMemories, setRelatedMemories] = useState<RelatedMemory[]>([])
  const [isLoadingContext, setIsLoadingContext] = useState(false)
  const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [sessions, setSessions] = useState<ChatSessionResponse[]>([])
  const [showSessionPicker, setShowSessionPicker] = useState(false)

  // Debounced fetch for related memories
  const loadRelatedMemories = useCallback(async (text: string) => {
    if (!text || text.trim().length < 20) {
      setRelatedMemories([])
      return
    }
    setIsLoadingContext(true)
    try {
      const data = await fetchRelatedMemoriesApi(text)
      setRelatedMemories(data.memories || [])
    } catch (e) {
      console.error('Failed to fetch related memories', e)
    } finally {
      setIsLoadingContext(false)
    }
  }, [])

  // Debounce content changes
  useEffect(() => {
    const timer = setTimeout(() => {
      loadRelatedMemories(content)
    }, 1500) // 1.5초 후 검색
    return () => clearTimeout(timer)
  }, [content, loadRelatedMemories])

  const showSaveStatus = (type: 'success' | 'error', message: string) => {
    setSaveStatus({ type, message })
    setTimeout(() => setSaveStatus(null), 3000)
  }

  const handleGenerateDraft = async () => {
    setIsGenerating(true)
    try {
      const sessionList = await fetchChatSessions()
      if (sessionList.length === 0) {
        showSaveStatus('error', '대화 세션이 없습니다. 먼저 Evening 모드로 대화해보세요.')
        return
      }
      setSessions(sessionList)
      setShowSessionPicker(true)
    } catch (e) {
      console.error(e)
      showSaveStatus('error', '세션 목록을 불러오지 못했습니다.')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSelectSession = async (sessionId: string) => {
    setShowSessionPicker(false)
    setIsGenerating(true)
    try {
      const result = await generateJournalDraft(sessionId)
      setContent(result.draft)
      showSaveStatus('success', 'AI 초안이 생성되었습니다!')
    } catch (e) {
      console.error(e)
      showSaveStatus('error', '초안 생성에 실패했습니다.')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSave = async () => {
    if (!content.trim()) return
    setIsSaving(true)
    try {
      await saveJournal(content)
      showSaveStatus('success', '저장되었습니다!')
    } catch (e) {
      console.error(e)
      showSaveStatus('error', '저장에 실패했습니다.')
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
                {saveStatus && (
                    <span className={`save-status save-status--${saveStatus.type}`}>
                        {saveStatus.message}
                    </span>
                )}
                <button
                    className="generate-btn"
                    onClick={handleGenerateDraft}
                    disabled={isGenerating}
                >
                    {isGenerating ? 'Generating...' : 'AI Draft'}
                </button>
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
      
      {/* Session Picker Modal */}
      {showSessionPicker && (
        <div className="session-picker-overlay" onClick={() => setShowSessionPicker(false)}>
          <div className="session-picker" onClick={(e) => e.stopPropagation()}>
            <h3>대화 세션 선택</h3>
            <p className="session-picker-desc">저널로 정리할 대화를 선택하세요</p>
            <div className="session-list">
              {sessions.map(session => (
                <button
                  key={session.id}
                  className="session-item"
                  onClick={() => handleSelectSession(session.id)}
                >
                  <span className="session-title">{session.title}</span>
                  <span className="session-date">
                    {new Date(session.created_at).toLocaleDateString('ko-KR')}
                  </span>
                </button>
              ))}
            </div>
            <button className="session-cancel" onClick={() => setShowSessionPicker(false)}>
              취소
            </button>
          </div>
        </div>
      )}

      <div className="companion-section">
        <div className="companion-header">
            <h3>Thinking Partner</h3>
        </div>
        <div className="chat-wrapper">
             <ChatView />
        </div>
      </div>
    </div>
  )
}

