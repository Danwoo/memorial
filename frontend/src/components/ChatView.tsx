import { useState, useRef, useEffect, type ReactNode } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  User, Bot, MessageSquareText, ArrowUp,
  MessageSquare, Lightbulb, Scale, ClipboardList, Moon, ChevronDown,
} from 'lucide-react'
import type { ChatMessage, ChatMode, ChatModeOption, ChatLocationState, DigestData } from '../types'
import { createChatSession, fetchChatHistory, sendChatMessage, readSSEStream, fetchDigest } from '../api'
import './ChatView.css'

// Lucide icon map keyed by mode value (avoids changing ChatModeOption.icon type)
const MODE_ICONS: Record<string, ReactNode> = {
  '': <MessageSquare size={16} />,
  'insight': <Lightbulb size={16} />,
  'counter': <Scale size={16} />,
  'summary': <ClipboardList size={16} />,
  'evening': <Moon size={16} />,
}

const MODES: ChatModeOption[] = [
  { value: '', label: '기본', icon: 'message-square', desc: '일반 대화' },
  { value: 'insight', label: '인사이트', icon: 'lightbulb', desc: '깊은 질문으로 사고 확장' },
  { value: 'counter', label: '반론', icon: 'scale', desc: '반대 의견 제시' },
  { value: 'summary', label: '요약', icon: 'clipboard-list', desc: '대화 내용 정리' },
  { value: 'evening', label: '저녁 회고', icon: 'moon', desc: '하루 돌아보기' },
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
  const [digest, setDigest] = useState<DigestData | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const modeDropdownRef = useRef<HTMLDivElement>(null)

  // URL 파라미터로 진입 시 채팅 히스토리 로드 (예: /chat/abc-123)
  // sessionId를 의존성에서 제외: setSessionId가 재렌더링을 유발해 무한루프 방지
  useEffect(() => {
    if (urlSessionId && urlSessionId !== sessionId) {
      setSessionId(urlSessionId)
      loadHistory(urlSessionId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSessionId])

  // location state 처리: 새 세션 시작 또는 GraphView에서 전달된 토픽
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

  // 드롭다운 외부 클릭 시 닫기
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (modeDropdownRef.current && !modeDropdownRef.current.contains(e.target as Node)) {
        setShowModes(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 마운트 시 다이제스트 로드 (빈 상태 표시용)
  useEffect(() => {
    fetchDigest().then(setDigest).catch(() => {})
  }, [])

  // 언마운트 시 진행 중인 SSE 스트림 중단
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
      // 세션이 없으면 새로 생성
      let currentSessionId = sessionId
      if (!currentSessionId) {
        const session = await createChatSession()
        currentSessionId = session.id
        setSessionId(currentSessionId)
        // URL에 세션 ID 반영 (히스토리 교체)
        navigate(`/chat/${currentSessionId}`, { replace: true })
      }

      // 메시지 전송 후 SSE 응답 수신
      const response = await sendChatMessage(
        currentSessionId,
        { content: userMessage, mode: mode || undefined },
        abortController.signal,
      )

      // 어시스턴트 메시지 플레이스홀더 추가
      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      // SSE 스트림을 읽으며 실시간으로 메시지 업데이트
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

  const handleSuggestedQuestion = (question: string) => {
    setInput(question)
  }

  const currentMode = MODES.find(m => m.value === mode) || MODES[0]

  return (
    <div className="chat-view">
      <div className="chat-header">
        <div>
          <h1>Socrates</h1>
          <p className="chat-subtitle">당신의 지적 동반자</p>
        </div>
        <div className="mode-selector" ref={modeDropdownRef}>
          <button
            className="mode-toggle"
            onClick={() => setShowModes(!showModes)}
          >
            <span className="mode-icon">{MODE_ICONS[currentMode.value]}</span>
            <span>{currentMode.label}</span>
            <ChevronDown size={14} />
          </button>
          {showModes && (
            <div className="mode-dropdown">
              {MODES.map(m => (
                <button
                  key={m.value}
                  className={`mode-option ${mode === m.value ? 'active' : ''}`}
                  onClick={() => { setMode(m.value); setShowModes(false) }}
                >
                  <span className="mode-icon">{MODE_ICONS[m.value]}</span>
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
            <div className="loading-spinner"></div>
            <p>대화 기록을 불러오는 중...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-empty">
            <MessageSquareText size={48} className="state-icon" />
            <h2>무엇이 궁금하신가요?</h2>
            <p>저장된 지식을 바탕으로 대화해보세요</p>

            {digest && (digest.summary.memory_count > 0 || digest.insights.main_topics.length > 0) && (
              <div className="welcome-stats">
                <span>오늘 메모리 {digest.summary.memory_count}개</span>
                <span className="welcome-stats-dot">&middot;</span>
                <span>주제 {digest.insights.main_topics.length}개</span>
              </div>
            )}

            {digest && digest.insights.suggested_questions.length > 0 && (
              <div className="suggested-questions">
                {digest.insights.suggested_questions.map((q, idx) => (
                  <button key={idx} className="suggested-q" onClick={() => handleSuggestedQuestion(q)}>
                    {q}
                  </button>
                ))}
              </div>
            )}

            {mode && (
              <div className="mode-active-hint">
                {MODE_ICONS[currentMode.value]} <strong>{currentMode.label}</strong> 모드 활성화됨
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
                {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
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
            {isLoading ? <div className="loading-spinner small" /> : <ArrowUp size={18} />}
          </button>
        </div>
      </div>
    </div>
  )
}
