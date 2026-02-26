import { useState, useRef, useEffect, useCallback } from 'react'
import { useLocation, useNavigate, useParams } from 'react-router-dom'
import { useSocratesSession } from '../contexts/SocratesSessionContext'
import { useToast } from '../contexts/ToastContext'
import { useDemoMode } from '../contexts/DemoContext'
import type { SocratesMessage, SocratesLocationState, BriefingData, SocratesFeedback, SocratesMessagePayload, SourceContext, SocratesMode } from '../types'
import {
  createSocratesSession, fetchSocratesHistory, sendSocratesMessage, readSSEStream,
  fetchBriefing, sendFeedback, fetchFeedbacks, createScrap,
} from '../api'

const ERROR_MESSAGE = '죄송합니다, 오류가 발생했습니다. 다시 시도해주세요.'

export interface SocratesChatContext {
  type: 'diary' | 'scrap' | 'mindmap'
  content?: string
  title?: string
  tags?: string[]
  graph_neighbors?: Array<{ name: string; label: string; relation_type: string }>
}

export interface UseSocratesChatOptions {
  mode: 'standalone' | 'panel'
  context?: SocratesChatContext
  initialMessage?: string
}

export interface UseSocratesChatReturn {
  sessionId: string | null
  messages: SocratesMessage[]
  input: string
  setInput: (v: string) => void
  isLoading: boolean
  isLoadingHistory: boolean
  briefing: BriefingData | null
  expandedRefs: Set<number>
  feedbacks: Map<number, 'good' | 'bad'>
  showScrollBtn: boolean
  messagesEndRef: React.RefObject<HTMLDivElement>
  messagesContainerRef: React.RefObject<HTMLDivElement>
  textareaRef: React.RefObject<HTMLTextAreaElement>
  handleSendMessage: () => void
  handleFeedback: (msgIndex: number, rating: 'good' | 'bad') => void
  scrollToBottom: () => void
  handleMessagesScroll: () => void
  adjustTextareaHeight: () => void
  handleKeyDown: (e: React.KeyboardEvent) => void
  toggleRefExpand: (idx: number) => void
  setSourceContextOverride: (ctx: SocratesChatContext | null) => void
  saveMessageAsScrap: (content: string) => void
  selectedMode: SocratesMode
  setSelectedMode: (mode: SocratesMode) => void
  hasBriefingContent: boolean
  sendMessageDirect: (text: string) => void
}

export function useSocratesChat(options: UseSocratesChatOptions): UseSocratesChatReturn {
  const { mode } = options
  const isStandalone = mode === 'standalone'

  const location = useLocation()
  const navigate = useNavigate()
  const { sessionId: urlSessionId } = useParams<{ sessionId: string }>()
  const { triggerRefresh } = useSocratesSession()
  const toast = useToast()
  const { isDemoMode: isDemo } = useDemoMode()
  const pathPrefix = isDemo ? '/demo' : ''

  const [sessionId, setSessionId] = useState<string | null>(
    isStandalone ? (urlSessionId ?? null) : null,
  )
  const [messages, setMessages] = useState<SocratesMessage[]>([])
  const [input, setInput] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [briefing, setBriefing] = useState<BriefingData | null>(null)
  const [expandedRefs, setExpandedRefs] = useState<Set<number>>(new Set())
  const [feedbacks, setFeedbacks] = useState<Map<number, 'good' | 'bad'>>(new Map())
  const [showScrollBtn, setShowScrollBtn] = useState(false)
  const [selectedMode, setSelectedMode] = useState<SocratesMode>('default')

  const messagesEndRef = useRef<HTMLDivElement>(null)
  const messagesContainerRef = useRef<HTMLDivElement>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const pendingMessageRef = useRef<string | null>(null)
  const handleSendRef = useRef<() => void>(() => {})
  const contextRef = useRef(options.context)
  const sourceContextOverrideRef = useRef<SocratesChatContext | null>(null)

  // URL 파라미터로 진입 시 채팅 히스토리 로드 (standalone 모드만)
  useEffect(() => {
    if (!isStandalone) return
    if (urlSessionId && urlSessionId !== sessionId) {
      setSessionId(urlSessionId)
      loadHistory(urlSessionId)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSessionId])

  // location state 처리 (standalone 모드만)
  useEffect(() => {
    if (!isStandalone) return
    const state = location.state as SocratesLocationState | null
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
  }, [location.state, isStandalone])

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

  // 옵션으로 전달된 initialMessage 처리
  useEffect(() => {
    if (options.initialMessage) {
      pendingMessageRef.current = options.initialMessage
      setInput(options.initialMessage)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [options.initialMessage])

  // context 최신 상태 동기화
  useEffect(() => {
    contextRef.current = options.context
  }, [options.context])

  // 마운트 시 브리핑 로드
  useEffect(() => {
    fetchBriefing().then(setBriefing).catch(() => {})
  }, [])

  // 언마운트 시 진행 중인 SSE 스트림 중단
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort()
    }
  }, [])

  // 스트리밍 중 탭/브라우저 닫기 경고
  useEffect(() => {
    if (!isLoading) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
      e.returnValue = ''
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isLoading])

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [])

  useEffect(() => {
    scrollToBottom()
  }, [messages, scrollToBottom])

  const handleMessagesScroll = useCallback(() => {
    const el = messagesContainerRef.current
    if (!el) return
    const distFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight
    setShowScrollBtn(distFromBottom > 200)
  }, [])

  const loadHistory = async (sid: string) => {
    setIsLoadingHistory(true)
    try {
      const [history, fbList] = await Promise.all([
        fetchSocratesHistory(sid),
        fetchFeedbacks(sid).catch(() => [] as SocratesFeedback[]),
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
      let currentSessionId = sessionId
      if (!currentSessionId) {
        const session = await createSocratesSession()
        currentSessionId = session.id
        setSessionId(currentSessionId)
        if (isStandalone) {
          navigate(`${pathPrefix}/diary`, { replace: true, state: { openSocrates: true, sessionId: currentSessionId } })
        }
      }

      const payload: SocratesMessagePayload = {
        content: userMessage,
        mode: selectedMode === 'default' ? undefined : selectedMode,
      }
      const ctx = sourceContextOverrideRef.current || contextRef.current
      if (ctx) {
        const sourceCtx: SourceContext = { type: ctx.type }
        if (ctx.title) sourceCtx.title = ctx.title
        if (ctx.content) sourceCtx.content_preview = ctx.content.slice(0, 500)
        if (ctx.tags) sourceCtx.tags = ctx.tags
        if (ctx.graph_neighbors) sourceCtx.graph_neighbors = ctx.graph_neighbors
        payload.source_context = sourceCtx
      }
      // 오버라이드는 첫 메시지에만 적용 후 초기화
      if (sourceContextOverrideRef.current) {
        sourceContextOverrideRef.current = null
      }

      const response = await sendSocratesMessage(
        currentSessionId,
        payload,
        abortController.signal,
      )

      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      const result = await readSSEStream(response, (accumulated) => {
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: accumulated }
          return updated
        })
      })

      if (result.references && result.references.length > 0) {
        setMessages(prev => {
          const updated = [...prev]
          const last = updated[updated.length - 1]
          updated[updated.length - 1] = { ...last, references: result.references }
          return updated
        })
      }

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
  }, [input, isLoading, sessionId, selectedMode, navigate, toast, triggerRefresh, pathPrefix, isStandalone])

  handleSendRef.current = handleSendMessage

  // 외부에서 직접 메시지를 보내는 함수
  const sendMessageDirect = useCallback((text: string) => {
    pendingMessageRef.current = text
    setInput(text)
  }, [])

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

  const setSourceContextOverride = useCallback((ctx: SocratesChatContext | null) => {
    sourceContextOverrideRef.current = ctx
  }, [])

  const saveMessageAsScrap = useCallback(async (content: string) => {
    try {
      await createScrap({
        sourceType: 'NOTE',
        content,
      })
      toast.success('스크랩으로 저장했습니다')
    } catch {
      toast.error('저장에 실패했습니다')
    }
  }, [toast])

  const hasBriefingContent = !!(briefing && (briefing.today_scraps?.count ?? 0) > 0)

  return {
    sessionId,
    messages,
    input,
    setInput,
    isLoading,
    isLoadingHistory,
    briefing,
    expandedRefs,
    feedbacks,
    showScrollBtn,
    messagesEndRef,
    messagesContainerRef,
    textareaRef,
    handleSendMessage,
    handleFeedback,
    scrollToBottom,
    handleMessagesScroll,
    adjustTextareaHeight,
    handleKeyDown,
    toggleRefExpand,
    hasBriefingContent,
    sendMessageDirect,
    setSourceContextOverride,
    saveMessageAsScrap,
    selectedMode,
    setSelectedMode,
  }
}
