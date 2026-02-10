import { useState, useRef, useEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import type { ChatMessage, ChatMode, ChatModeOption } from '../types'
import { createChatSession, sendChatMessage, readSSEStream } from '../api'
import './ChatView.css'

const MODES: ChatModeOption[] = [
  { value: '', label: '기본', icon: '💬', desc: '일반 대화' },
  { value: 'insight', label: '인사이트', icon: '💡', desc: '깊은 질문으로 사고 확장' },
  { value: 'counter', label: '반론', icon: '⚖️', desc: '반대 의견 제시' },
  { value: 'summary', label: '요약', icon: '📋', desc: '대화 내용 정리' },
  { value: 'evening', label: '저녁 회고', icon: '🌙', desc: '하루 돌아보기' }
]

/**
 * Embeddable chat component without routing.
 * Used inside JournalView's "Thinking Partner" section.
 */
export default function ChatWidget() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [mode, setMode] = useState<ChatMode>('')
  const [showModes, setShowModes] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

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

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    const abortController = new AbortController()
    abortControllerRef.current = abortController

    try {
      let currentSessionId = sessionId
      if (!currentSessionId) {
        const session = await createChatSession()
        currentSessionId = session.id
        setSessionId(currentSessionId)
      }

      const response = await sendChatMessage(
        currentSessionId,
        { content: userMessage, mode: mode || undefined },
        abortController.signal,
      )

      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

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
    <div className="chat-view chat-widget">
      <div className="chat-header">
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
        {messages.length === 0 ? (
          <div className="chat-empty">
            <div className="empty-icon">🤔</div>
            <p>글 작성 중 궁금한 점을 물어보세요</p>
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
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
