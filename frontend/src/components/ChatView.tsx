import { useState, useRef, useEffect } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage, ChatMode, ChatModeOption, ChatLocationState } from '../types'
import { createChatSession, fetchChatHistory, sendChatMessage, readSSEStream } from '../api'
import './ChatView.css'

const MODES: ChatModeOption[] = [
  { value: '', label: '기본', icon: '💬', desc: '일반 대화' },
  { value: 'insight', label: '인사이트', icon: '💡', desc: '깊은 질문으로 사고 확장' },
  { value: 'counter', label: '반론', icon: '⚖️', desc: '반대 의견 제시' },
  { value: 'summary', label: '요약', icon: '📋', desc: '대화 내용 정리' },
  { value: 'evening', label: '저녁 회고', icon: '🌙', desc: '하루 돌아보기' }
]

export default function ChatView() {
  const location = useLocation()
  const navigate = useNavigate()
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>()

  const [sessionId, setSessionId] = useState<string | null>(urlSessionId ?? null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [mode, setMode] = useState<ChatMode>('')
  const [showModes, setShowModes] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Load history when entering via URL param (e.g. /chat/abc-123)
  useEffect(() => {
    if (urlSessionId && urlSessionId !== sessionId) {
      setSessionId(urlSessionId)
      loadHistory(urlSessionId)
    }
  }, [urlSessionId])

  // Handle location state: newSession or topic from GraphView
  useEffect(() => {
    const state = location.state as ChatLocationState | null
    if (state?.newSession) {
      setSessionId(null)
      setMessages([])
      window.history.replaceState({}, '')
    } else if (state?.topic) {
      setSessionId(null)
      setMessages([])
      if (state.mode) setMode(state.mode as ChatMode)
      const topicMessage = `${state.topic}에 대해 이야기하고 싶어. 내가 저장한 관련 지식을 바탕으로 대화해줘.`
      setInput(topicMessage)
      window.history.replaceState({}, '')
    }
  }, [location.state])

  // Cleanup: abort any in-flight SSE stream on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const loadHistory = async (sid: string) => {
    setIsLoadingHistory(true)
    try {
      const history = await fetchChatHistory(sid)
      setMessages(history)
    } catch (error) {
      console.error('Failed to load chat history:', error)
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    const abortController = new AbortController()
    abortControllerRef.current = abortController

    try {
      // Create session if needed
      let currentSessionId = sessionId
      if (!currentSessionId) {
        const session = await createChatSession()
        currentSessionId = session.id
        setSessionId(currentSessionId)
        // Update URL to include session ID (replace, not push)
        navigate(`/chat/${currentSessionId}`, { replace: true })
      }

      // Send message and get SSE response
      const response = await sendChatMessage(
        currentSessionId,
        { content: userMessage, mode: mode || undefined },
        abortController.signal,
      )

      // Add placeholder for assistant message
      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      // Stream the response
      await readSSEStream(response, (accumulated) => {
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: accumulated }
          return updated
        })
      })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') {
        return
      }
      console.error('Error sending message:', error)
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '죄송합니다, 오류가 발생했습니다. 다시 시도해주세요.'
      }])
    } finally {
      abortControllerRef.current = null
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const currentMode = MODES.find(m => m.value === mode) || MODES[0]

  return (
    <div className="chat-view">
      <div className="chat-header">
        <div>
          <h1>Socrates</h1>
          <p className="chat-subtitle">당신의 지적 동반자</p>
        </div>
        <div className="mode-selector">
          <button
            className="mode-toggle"
            onClick={() => setShowModes(!showModes)}
          >
            <span>{currentMode.icon}</span>
            <span>{currentMode.label}</span>
            <span className="mode-arrow">▼</span>
          </button>
          {showModes && (
            <div className="mode-dropdown">
              {MODES.map(m => (
                <button
                  key={m.value}
                  className={`mode-option ${mode === m.value ? 'active' : ''}`}
                  onClick={() => { setMode(m.value); setShowModes(false) }}
                >
                  <span className="mode-icon">{m.icon}</span>
                  <div className="mode-info">
                    <span className="mode-label">{m.label}</span>
                    <span className="mode-desc">{m.desc}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="chat-messages">
        {isLoadingHistory ? (
          <div className="chat-empty">
            <div className="empty-icon">...</div>
            <p>대화 기록을 불러오는 중...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-empty">
            <div className="empty-icon">🤔</div>
            <h2>무엇이 궁금하신가요?</h2>
            <p>저장된 지식을 바탕으로 대화해보세요</p>
            {mode && (
              <div className="mode-active-hint">
                {currentMode.icon} <strong>{currentMode.label}</strong> 모드 활성화됨
              </div>
            )}
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div
              key={idx}
              className={`message ${msg.role}`}
            >
              <div className="message-avatar">
                {msg.role === 'user' ? '👤' : '🧠'}
              </div>
              <div className="message-content">
                {msg.role === 'assistant' ? (
                  msg.content ? (
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {msg.content}
                    </ReactMarkdown>
                  ) : (
                    <span className="typing-indicator">...</span>
                  )
                ) : (
                  msg.content || <span className="typing-indicator">...</span>
                )}
              </div>
            </div>
          ))
        )}
        <div ref={messagesEndRef} />
      </div>

      <div className="chat-input-container">
        <div className="chat-input-wrapper">
          <textarea
            className="chat-input"
            placeholder="메시지를 입력하세요..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            rows={1}
            disabled={isLoading}
          />
          <button
            className="send-button"
            onClick={handleSendMessage}
            disabled={!input.trim() || isLoading}
          >
            {isLoading ? '...' : '→'}
          </button>
        </div>
      </div>
    </div>
  )
}
