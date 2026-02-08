import { useState, useRef, useEffect } from 'react'
import './ChatView.css'

interface Message {
  role: 'user' | 'assistant'
  content: string
}

interface ChatViewProps {
  sessionId: string | null
  onSessionCreate: (id: string) => void
}

type ChatMode = '' | 'insight' | 'counter' | 'summary' | 'evening'

const MODES: { value: ChatMode; label: string; icon: string; desc: string }[] = [
  { value: '', label: '기본', icon: '💬', desc: '일반 대화' },
  { value: 'insight', label: '인사이트', icon: '💡', desc: '깊은 질문으로 사고 확장' },
  { value: 'counter', label: '반론', icon: '⚖️', desc: '반대 의견 제시' },
  { value: 'summary', label: '요약', icon: '📋', desc: '대화 내용 정리' },
  { value: 'evening', label: '저녁 회고', icon: '🌙', desc: '하루 돌아보기' }
]

const API_BASE = '/api/v1'

export default function ChatView({ sessionId, onSessionCreate }: ChatViewProps) {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [mode, setMode] = useState<ChatMode>('')
  const [showModes, setShowModes] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const createSession = async (): Promise<string> => {
    const res = await fetch(`${API_BASE}/chat/sessions`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({})
    })
    const data = await res.json()
    return data.id
  }

  const sendMessage = async () => {
    if (!input.trim() || isLoading) return
    
    const userMessage = input.trim()
    setInput('')
    setMessages(prev => [...prev, { role: 'user', content: userMessage }])
    setIsLoading(true)

    try {
      // Create session if needed
      let currentSessionId = sessionId
      if (!currentSessionId) {
        currentSessionId = await createSession()
        onSessionCreate(currentSessionId)
      }

      // Send message via SSE with mode
      const res = await fetch(`${API_BASE}/chat/sessions/${currentSessionId}/messages`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
          content: userMessage,
          mode: mode || undefined
        })
      })

      if (!res.ok) throw new Error('Failed to send message')

      // Read SSE stream
      const reader = res.body?.getReader()
      const decoder = new TextDecoder()
      let assistantContent = ''

      if (reader) {
        // Add placeholder for assistant message
        setMessages(prev => [...prev, { role: 'assistant', content: '' }])

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          const lines = chunk.split('\n')

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6))
                if (data.content) {
                  assistantContent += data.content
                  setMessages(prev => {
                    const updated = [...prev]
                    updated[updated.length - 1] = { role: 'assistant', content: assistantContent }
                    return updated
                  })
                }
              } catch {
                // Ignore parse errors
              }
            }
          }
        }
      }
    } catch (error) {
      console.error('Error sending message:', error)
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: '죄송합니다, 오류가 발생했습니다. 다시 시도해주세요.' 
      }])
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
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
        {messages.length === 0 ? (
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
                {msg.content || <span className="typing-indicator">...</span>}
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
            onClick={sendMessage}
            disabled={!input.trim() || isLoading}
          >
            {isLoading ? '...' : '→'}
          </button>
        </div>
      </div>
    </div>
  )
}
