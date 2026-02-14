import { useState, useRef, useEffect, useCallback } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  User, Bot, MessageSquareText, ArrowUp,
  BookOpen, X, Paperclip, ChevronDown, ChevronUp, FileText, Globe, StickyNote,
} from 'lucide-react'
import { useToast } from '../contexts/ToastContext'
import type { ChatMessage, ChatLocationState, BriefingData } from '../types'
import { createChatSession, fetchChatHistory, sendChatMessage, readSSEStream, fetchBriefing } from '../api'
import './ChatView.css'

const ERROR_MESSAGE = '죄송합니다, 오류가 발생했습니다. 다시 시도해주세요.'

export default function ChatView() {
  const location = useLocation()
  const navigate = useNavigate()
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>()
  const toast = useToast()

  const [sessionId, setSessionId] = useState<string | null>(urlSessionId ?? null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [briefing, setBriefing] = useState<BriefingData | null>(null)
  const [expandedRefs, setExpandedRefs] = useState<Set<number>>(new Set())
  const [welcomeDismissed, setWelcomeDismissed] = useState(
    () => localStorage.getItem('memoir-welcome-dismissed') === 'true'
  )
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)

  // URL 파라미터로 진입 시 채팅 히스토리 로드 (예: /chat/abc-123)
  // sessionId를 의존성에서 제외: setSessionId가 재렌더링을 유발해 무한루프 방지
  useEffect(() => {
    if (urlSessionId && urlSessionId !== sessionId) {
      setSessionId(urlSessionId)
      loadHistory(urlSessionId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSessionId])

  // location state 처리: 새 세션 시작, GraphView 토픽, 온보딩 질문
  const pendingMessageRef = useRef<string | null>(null)

  useEffect(() => {
    const state = location.state as ChatLocationState | null
    if (state?.newSession) {
      setSessionId(null)
      setMessages([])
      window.history.replaceState({}, '')
    } else if (state?.topic) {
      setSessionId(null)
      setMessages([])
      setInput(`${state.topic}에 대해 이야기하고 싶어. 내가 저장한 관련 지식을 바탕으로 대화해줘.`)
      window.history.replaceState({}, '')
    } else if (state?.initialMessage) {
      setSessionId(null)
      setMessages([])
      pendingMessageRef.current = state.initialMessage
      setInput(state.initialMessage)
      window.history.replaceState({}, '')
    }
  }, [location.state])

  // 온보딩 등에서 전달된 initialMessage 자동 전송
  useEffect(() => {
    if (pendingMessageRef.current && input === pendingMessageRef.current && !isLoading) {
      pendingMessageRef.current = null
      const timer = setTimeout(() => {
        handleSendMessage()
      }, 100)
      return () => clearTimeout(timer)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [input, isLoading])

  // 마운트 시 브리핑 로드 (빈 상태 표시용)
  useEffect(() => {
    fetchBriefing().then(setBriefing).catch(() => {})
  }, [])

  // 언마운트 시 진행 중인 SSE 스트림 중단
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const loadHistory = async (sid: string) => {
    setIsLoadingHistory(true)
    try {
      const history = await fetchChatHistory(sid)
      setMessages(history)
    } catch (error) {
      console.error('채팅 히스토리 로드 실패:', error)
      toast.error('대화 기록을 불러오지 못했습니다.')
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const handleSendMessage = async () => {
    if (!input.trim() || isLoading) return

    const userMessage = input.trim()
    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
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
        navigate(`/chat/${currentSessionId}`, { replace: true })
      }

      const response = await sendChatMessage(
        currentSessionId,
        { content: userMessage },
        abortController.signal,
      )

      // 어시스턴트 메시지 플레이스홀더 추가 후 SSE 스트림으로 실시간 갱신
      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      const result = await readSSEStream(response, (accumulated) => {
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: accumulated }
          return updated
        })
      })

      // 참조 메모리가 있으면 마지막 어시스턴트 메시지에 첨부
      if (result.references && result.references.length > 0) {
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          updated[updated.length - 1] = { ...last, references: result.references }
          return updated
        })
      }

      // 세션 제목이 자동 생성되면 사이드바에 알림
      if (result.title) {
        window.dispatchEvent(new CustomEvent('session-title-updated'))
      }
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') return
      console.error('메시지 전송 실패:', error)
      toast.error('메시지 전송에 실패했습니다.')
      setMessages(prev => [...prev, { role: 'assistant', content: ERROR_MESSAGE }])
    } finally {
      abortControllerRef.current = null
      setIsLoading(false)
    }
  }

  const adjustTextareaHeight = useCallback(() => {
    const textarea = textareaRef.current
    if (!textarea) return
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`
  }, [])

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage()
    }
  }

  const dismissWelcome = useCallback(() => {
    localStorage.setItem('memoir-welcome-dismissed', 'true')
    setWelcomeDismissed(true)
  }, [])

  const toggleRefExpand = useCallback((idx: number) => {
    setExpandedRefs(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }, [])

  const getSourceIcon = (sourceType: string) => {
    switch (sourceType) {
      case 'WEB': return <Globe size={14} />
      case 'PDF': return <FileText size={14} />
      default: return <StickyNote size={14} />
    }
  }

  const showWelcomeBanner = briefing !== null
    && briefing.today_memories.count === 0
    && !welcomeDismissed

  const hasBriefingContent = briefing && briefing.today_memories.count > 0

  return (
    <div className="chat-view">
      <div className="chat-header">
        <div>
          <h1>Socrates</h1>
          <p className="chat-subtitle">당신의 지적 동반자</p>
        </div>
      </div>

      <div className="chat-messages" aria-live="polite" aria-label="대화 메시지">
        {isLoadingHistory ? (
          <div className="chat-empty">
            <div className="loading-spinner"></div>
            <p>대화 기록을 불러오는 중...</p>
          </div>
        ) : messages.length === 0 ? (
          <div className="chat-empty">
            {showWelcomeBanner && (
              <div className="welcome-banner">
                <button className="welcome-banner-close" onClick={dismissWelcome} type="button">
                  <X size={16} />
                </button>
                <BookOpen size={32} className="welcome-banner-icon" />
                <h3>Memoir에 오신 것을 환영합니다!</h3>
                <p>웹 페이지, 메모, PDF 등을 저장하면 AI가 지식을 연결해줍니다.</p>
                <button
                  className="welcome-banner-cta"
                  onClick={() => navigate('/memories')}
                  type="button"
                >
                  메모리 추가하기
                </button>
              </div>
            )}

            <MessageSquareText size={48} className="state-icon" />
            {hasBriefingContent ? (
              <>
                <h2>오늘 {briefing.today_memories.count}개의 기억이 쌓였습니다</h2>
                <p>무엇이 궁금하세요?</p>
                {briefing.today_memories.topics.length > 0 && (
                  <div className="welcome-stats">
                    {briefing.today_memories.topics.map((t, i) => (
                      <span key={i} className="welcome-topic-tag">#{t}</span>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <>
                <h2>무엇이 궁금하신가요?</h2>
                <p>저장된 지식을 바탕으로 대화해보세요</p>
              </>
            )}

            {briefing && (
              <div className="suggested-questions">
                <button className="suggested-q" onClick={() => setInput(briefing.suggested_question)}>
                  {briefing.suggested_question}
                </button>
                <button className="suggested-q" onClick={() => setInput('최근 관심사에 대해 이야기해줘')}>
                  최근 관심사에 대해 이야기해줘
                </button>
                <button className="suggested-q" onClick={() => setInput('저장한 글 중 인상적인 것은?')}>
                  저장한 글 중 인상적인 것은?
                </button>
              </div>
            )}
          </div>
        ) : (
          messages.map((msg, idx) => (
            <div key={idx} className={`message ${msg.role}`}>
              <div className="message-avatar">
                {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
              </div>
              <div className="message-content">
                {msg.role === 'assistant' ? (
                  msg.content ? (
                    <>
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>
                        {msg.content}
                      </ReactMarkdown>
                      {msg.references && msg.references.length > 0 && (
                        <div className="chat-references">
                          <button
                            className="chat-references-toggle"
                            onClick={() => toggleRefExpand(idx)}
                            type="button"
                          >
                            <Paperclip size={14} />
                            <span>{msg.references.length}개 기억 참조</span>
                            {expandedRefs.has(idx) ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                          </button>
                          {expandedRefs.has(idx) && (
                            <div className="chat-references-list">
                              {msg.references.map(ref => (
                                <button
                                  key={ref.id}
                                  className="chat-reference-chip"
                                  onClick={() => navigate(`/memories`)}
                                  type="button"
                                >
                                  {getSourceIcon(ref.source_type)}
                                  <span className="chat-reference-title">{ref.title}</span>
                                  <span className="chat-reference-date">{ref.created_at}</span>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                    </>
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
            ref={textareaRef}
            className="chat-input"
            placeholder="메시지를 입력하세요..."
            value={input}
            onChange={(e) => {
              setInput(e.target.value)
              adjustTextareaHeight()
            }}
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
