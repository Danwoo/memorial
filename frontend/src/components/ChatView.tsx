import { useState, useRef, useEffect, useCallback } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import {
  User, Bot, ArrowUp,
  Paperclip, ChevronDown, ChevronUp,
  ThumbsUp, ThumbsDown,
} from 'lucide-react'
import { useChatSession } from '../contexts/ChatSessionContext'
import { useToast } from '../contexts/ToastContext'
import { useDemoMode } from '../contexts/DemoContext'
import type { ChatMessage, ChatLocationState, BriefingData, ChatFeedback } from '../types'
import { createChatSession, fetchChatHistory, sendChatMessage, readSSEStream, fetchBriefing, sendFeedback, fetchFeedbacks } from '../api'
import SourceIcon from './shared/SourceIcon'
import './ChatView.css'

const ERROR_MESSAGE = '죄송합니다, 오류가 발생했습니다. 다시 시도해주세요.'

export default function ChatView() {
  const location = useLocation()
  const navigate = useNavigate()
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>()
  const { triggerRefresh } = useChatSession()
  const toast = useToast()
  const { isDemoMode: isDemo } = useDemoMode()
  const pathPrefix = isDemo ? '/demo' : ''

  const [sessionId, setSessionId] = useState<string | null>(urlSessionId ?? null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [briefing, setBriefing] = useState<BriefingData | null>(null)
  const [expandedRefs, setExpandedRefs] = useState<Set<number>>(new Set())
  const [feedbacks, setFeedbacks] = useState<Map<number, 'good' | 'bad'>>(new Map())
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
  const handleSendRef = useRef<() => void>(() => {})

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
        handleSendRef.current()
      }, 100)
      return () => clearTimeout(timer)
    }
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
      const [history, fbList] = await Promise.all([
        fetchChatHistory(sid),
        fetchFeedbacks(sid).catch(() => [] as ChatFeedback[]),
      ])
      setMessages(history)
      const fbMap = new Map<number, 'good' | 'bad'>()
      fbList.forEach(fb => fbMap.set(fb.message_index, fb.rating))
      setFeedbacks(fbMap)
    } catch (error) {
      console.error('채팅 히스토리 로드 실패:', error)
      toast.error('대화 기록을 불러오지 못했습니다.')
    } finally {
      setIsLoadingHistory(false)
    }
  }

  const handleFeedback = async (msgIndex: number, rating: 'good' | 'bad') => {
    if (!sessionId) return
    const current = feedbacks.get(msgIndex)
    if (current === rating) return
    setFeedbacks(prev => new Map(prev).set(msgIndex, rating))
    try {
      await sendFeedback(sessionId, msgIndex, rating)
    } catch {
      setFeedbacks(prev => {
        const next = new Map(prev)
        if (current) next.set(msgIndex, current)
        else next.delete(msgIndex)
        return next
      })
    }
  }

  const handleSendMessage = useCallback(async () => {
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
        navigate(`${pathPrefix}/chat/${currentSessionId}`, { replace: true })
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
        triggerRefresh()
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
  }, [input, isLoading, sessionId, navigate, toast, triggerRefresh, pathPrefix])

  handleSendRef.current = handleSendMessage

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

  const toggleRefExpand = useCallback((idx: number) => {
    setExpandedRefs(prev => {
      const next = new Set(prev)
      if (next.has(idx)) next.delete(idx)
      else next.add(idx)
      return next
    })
  }, [])

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
            <div className="chat-empty-branding">
              <Bot size={56} className="chat-empty-icon" />
              <h2 className="chat-empty-title">Socrates</h2>
              <p className="chat-empty-tagline">당신의 기억을 아는 지적 동반자</p>
            </div>
            {hasBriefingContent && (
              <div className="chat-empty-briefing">
                <p>오늘 {briefing.today_memories.count}개의 기억이 쌓였습니다</p>
                {briefing.today_memories.topics.length > 0 && (
                  <div className="welcome-stats">
                    {briefing.today_memories.topics.map((t, i) => (
                      <span key={i} className="welcome-topic-tag">#{t}</span>
                    ))}
                  </div>
                )}
              </div>
            )}

            <div className="suggested-questions">
              {briefing?.suggested_question && (
                <button className="suggested-q" onClick={() => { pendingMessageRef.current = briefing.suggested_question; setInput(briefing.suggested_question) }}>
                  {briefing.suggested_question}
                </button>
              )}
              <button className="suggested-q" onClick={() => { pendingMessageRef.current = '최근 관심사에 대해 이야기해줘'; setInput('최근 관심사에 대해 이야기해줘') }}>
                최근 관심사에 대해 이야기해줘
              </button>
              <button className="suggested-q" onClick={() => { pendingMessageRef.current = '저장한 글 중 인상적인 것은?'; setInput('저장한 글 중 인상적인 것은?') }}>
                저장한 글 중 인상적인 것은?
              </button>
            </div>
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
                            <span className="chat-references-label">{msg.references.length}개 기억 참조</span>
                            <span className="chat-references-badge">{msg.references.length}</span>
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
                                  <SourceIcon type={ref.source_type} size={14} />
                                  <span className="chat-reference-title">{ref.title}</span>
                                  <span className="chat-reference-date">{ref.created_at}</span>
                                </button>
                              ))}
                            </div>
                          )}
                        </div>
                      )}
                      <div className="chat-feedback-buttons">
                        <button
                          type="button"
                          className={`chat-feedback-btn${feedbacks.get(idx) === 'good' ? ' active' : ''}`}
                          onClick={() => handleFeedback(idx, 'good')}
                          title="도움이 됐어요"
                        >
                          <ThumbsUp size={14} />
                        </button>
                        <button
                          type="button"
                          className={`chat-feedback-btn${feedbacks.get(idx) === 'bad' ? ' active bad' : ''}`}
                          onClick={() => handleFeedback(idx, 'bad')}
                          title="아쉬워요"
                        >
                          <ThumbsDown size={14} />
                        </button>
                      </div>
                    </>
                  ) : (
                    <div className="typing-indicator-container">
                      <div className="typing-dots">
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                        <span className="typing-dot" />
                      </div>
                      <span className="typing-text">Socrates가 생각하고 있습니다...</span>
                    </div>
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
