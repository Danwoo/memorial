import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useLocation } from 'react-router-dom'
import { Save, Loader2, Check, PanelLeftClose, PanelRightClose, PanelLeftOpen, PanelRightOpen, Bot, Brain } from 'lucide-react'
import { useToast } from '../contexts/ToastContext'
import { useIsMobile } from '../hooks/useMediaQuery'
import { useSocratesChat } from '../hooks/useSocratesChat'
import TurndownService from 'turndown'
import type { EditorMode, RelatedMemory, DigestMemory, DigestData, ChatSessionResponse, JournalDateInfo } from '../types'
import {
  saveJournal,
  fetchRelatedMemories as fetchRelatedMemoriesApi,
  generateJournalDraft,
  fetchChatSessions,
  fetchDigest,
  fetchReviewQuestions,
  fetchJournalDates,
  fetchJournalsByDate,
} from '../api'
import type { Editor } from '@tiptap/react'
import { TiptapEditor, type TiptapEditorHandle } from './journal/TiptapEditor'
import { EditorToolbar } from './journal/EditorToolbar'
import { MarkdownEditor } from './journal/MarkdownEditor'
import { ReadOnlyViewer } from './journal/ReadOnlyViewer'
import { MemorySidebar } from './journal/MemorySidebar'
import { AIBubbleMenu } from './journal/AIBubbleMenu'
import { AIPanel } from './journal/AIPanel'
import SocratesChatPanel from './chat/SocratesChatPanel'
import { SessionPickerModal } from './journal/SessionPickerModal'
import { JournalDateNav } from './journal/JournalDateNav'
import { JournalStarter } from './journal/JournalStarter'
import { useJournalAutosave } from '../hooks/useJournalAutosave'
import MemoryDetailModal from './MemoryDetailModal'
import './JournalView.css'

// 관련 메모리 검색을 트리거하기 위한 최소 글자 수
const MIN_CONTENT_LENGTH_FOR_RELATED = 20

// 관련 메모리 디바운스 지연 시간(ms)
const RELATED_MEMORIES_DEBOUNCE_MS = 1500

const JOURNAL_DRAFT_KEY = 'memoir-journal-draft'


const turndown = new TurndownService({
  headingStyle: 'atx',
  bulletListMarker: '-',
})

// 메모리 블록 → 마크다운 인용 블록 변환
turndown.addRule('memoryBlock', {
  filter: (node) => node.hasAttribute('data-memory-block'),
  replacement: (_content, node) => {
    const el = node as HTMLElement
    const type = el.querySelector('.memory-block-type')?.textContent || ''
    const title = el.querySelector('.memory-block-title')?.textContent || ''
    const summary = el.querySelector('.memory-block-summary')?.textContent || ''
    return `\n> **[${type}]** ${title}\n> ${summary}\n\n`
  },
})

// 간이 마크다운 → HTML 변환 (Tiptap StarterKit 범위만 지원)
function markdownToHtml(md: string): string {
  return md
    .replace(/^### (.+)$/gm, '<h3>$1</h3>')
    .replace(/^## (.+)$/gm, '<h2>$1</h2>')
    .replace(/^# (.+)$/gm, '<h1>$1</h1>')
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.+?)\*/g, '<em>$1</em>')
    .replace(/~~(.+?)~~/g, '<s>$1</s>')
    .replace(/`(.+?)`/g, '<code>$1</code>')
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
    .replace(/^> (.+)$/gm, '<blockquote><p>$1</p></blockquote>')
    .replace(/^---$/gm, '<hr>')
    .replace(/^- (.+)$/gm, '<li>$1</li>')
    .replace(/(<li>.*?<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/^(?!<(?:h[1-6]|ul|ol|li|blockquote|hr|a|p|s|code|strong|em)[ >/])(.+)$/gm, '<p>$1</p>')
    .replace(/<\/blockquote>\s*<blockquote>/g, '\n')
}

/** 에디터 내용을 WYSIWYG 에디터에 동기화하는 헬퍼 */
function syncContentToEditor(
  content: string,
  editorMode: EditorMode,
  editorRef: React.RefObject<TiptapEditorHandle | null>,
) {
  if (editorMode === 'wysiwyg' && editorRef.current) {
    editorRef.current.setContent(markdownToHtml(content))
  }
}

// YYYY-MM-DD 형식 날짜 헬퍼 (로컬 타임존 기준)
function toDateStr(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, '0')
  const day = String(d.getDate()).padStart(2, '0')
  return `${y}-${m}-${day}`
}

function formatDateKo(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
}

export default function JournalView() {
  const todayStr = useMemo(() => toDateStr(new Date()), [])
  const todayLabel = formatDateKo(todayStr)
  const editorRef = useRef<TiptapEditorHandle>(null)
  const toast = useToast()
  const location = useLocation()

  // 날짜 네비게이션
  const [selectedDate, setSelectedDate] = useState(todayStr)
  const [journalDates, setJournalDates] = useState<JournalDateInfo[]>([])
  const [showDatePicker, setShowDatePicker] = useState(false)
  const isToday = selectedDate === todayStr

  const defaultContent = `# ${todayLabel} 회고\n\n오늘은...\n\n`
  const normalize = (s: string) => s.replace(/\s+/g, ' ').trim()

  const [markdownContent, setMarkdownContent] = useState(() => {
    if (!isToday) return ''
    const saved = localStorage.getItem(JOURNAL_DRAFT_KEY)
    return saved && saved.trim() ? saved : defaultContent
  })
  const [editorMode, setEditorMode] = useState<EditorMode>('wysiwyg')
  const [digest, setDigest] = useState<DigestData | null>(null)
  const [relatedMemories, setRelatedMemories] = useState<RelatedMemory[]>([])
  const [isLoadingRelated, setIsLoadingRelated] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [sessions, setSessions] = useState<ChatSessionResponse[]>([])
  const [showSessionPicker, setShowSessionPicker] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)

  const [tiptapEditor, setTiptapEditor] = useState<Editor | null>(null)
  const [starterQuestions, setStarterQuestions] = useState<string[]>([])
  const [isLoadingStarter, setIsLoadingStarter] = useState(false)
  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null)

  // 우측 패널 탭 (AI 분석 / Socrates)
  const [rightTab, setRightTab] = useState<'analysis' | 'socrates'>('analysis')

  // Socrates 채팅 훅
  const socratesChat = useSocratesChat({
    mode: 'panel',
    context: { type: 'journal', content: markdownContent },
  })

  // 모바일 탭 전환
  const isMobile = useIsMobile()
  const [mobileTab, setMobileTab] = useState<'editor' | 'memories' | 'ai'>('editor')

  // 좌/우 패널 collapse 상태
  const [leftCollapsed, setLeftCollapsed] = useState(() => {
    try {
      const saved = localStorage.getItem('memoir-journal-panels')
      return saved ? JSON.parse(saved).left ?? false : false
    } catch { return false }
  })
  const [rightCollapsed, setRightCollapsed] = useState(() => {
    try {
      const saved = localStorage.getItem('memoir-journal-panels')
      return saved ? JSON.parse(saved).right ?? false : false
    } catch { return false }
  })

  // collapse 상태 localStorage 저장
  useEffect(() => {
    localStorage.setItem('memoir-journal-panels', JSON.stringify({ left: leftCollapsed, right: rightCollapsed }))
  }, [leftCollapsed, rightCollapsed])

  const showStarter = isToday && normalize(markdownContent) === normalize(defaultContent) && !isGenerating

  const templates = useMemo(
    () => [
      {
        id: 'til',
        label: '오늘의 TIL',
        content: `# ${todayLabel} TIL\n\n## 오늘 배운 것\n\n\n\n## 느낀 점\n\n\n\n## 적용할 것\n\n`,
      },
      {
        id: 'weekly',
        label: '주간 회고',
        content: `# 이번 주 회고\n\n## 잘한 점\n\n\n\n## 아쉬운 점\n\n\n\n## 다음 주 계획\n\n`,
      },
      {
        id: 'project',
        label: '프로젝트 회고',
        content: `# ${todayLabel} 프로젝트 회고\n\n## 프로젝트 개요\n\n\n\n## 잘된 점\n\n\n\n## 개선할 점\n\n\n\n## 다음 단계\n\n`,
      },
      {
        id: 'free',
        label: '자유 회고',
        content: `# ${todayLabel} 회고\n\n`,
      },
    ],
    [todayLabel],
  )

  // Tiptap 에디터 HTML에서 삽입된 메모리 블록의 ID를 추출
  const extractMemoryIds = useCallback((): string[] => {
    if (editorMode !== 'wysiwyg' || !editorRef.current) return []
    const html = editorRef.current.getHTML()
    const ids: string[] = []
    // Tiptap은 camelCase 속성을 소문자로 렌더링: memoryId → memoryid
    const regex = /memoryid="([^"]+)"/g
    let match
    while ((match = regex.exec(html)) !== null) {
      if (match[1] && !ids.includes(match[1])) {
        ids.push(match[1])
      }
    }
    return ids
  }, [editorMode])

  // 서버 저장 함수 (useJournalAutosave에 전달)
  const serverSave = useCallback(async (content: string, memoryIds: string[]) => {
    await saveJournal(content, memoryIds)
  }, [])

  // 자동 저장 훅
  const { autoSaveStatus, isDirty, markSaved } = useJournalAutosave(
    markdownContent,
    defaultContent,
    isToday,
    extractMemoryIds,
    serverSave,
  )

  // 브라우저 탭 닫기/새로고침 시 미저장 내용 경고
  useEffect(() => {
    if (!isDirty) return
    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault()
    }
    window.addEventListener('beforeunload', handler)
    return () => window.removeEventListener('beforeunload', handler)
  }, [isDirty])

  // 다른 뷰에서 특정 날짜로 이동 / Socrates 열기 요청 시 처리
  useEffect(() => {
    const state = location.state as {
      date?: string
      openChat?: boolean
      topic?: string
      initialMessage?: string
    } | null
    if (!state) return
    if (state.date) {
      setSelectedDate(state.date)
    }
    if (state.openChat) {
      setRightTab('socrates')
      setRightCollapsed(false)
      if (isMobile) setMobileTab('ai')
      if (state.topic) {
        socratesChat.sendMessageDirect(
          `${state.topic}에 대해 이야기하고 싶어. 내가 저장한 관련 지식을 바탕으로 대화해줘.`,
        )
      } else if (state.initialMessage) {
        socratesChat.sendMessageDirect(state.initialMessage)
      }
    }
    window.history.replaceState({}, '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [location.state])

  // 마운트 시 저널 날짜 목록 로드
  useEffect(() => {
    fetchJournalDates()
      .then((res) => setJournalDates(res.dates))
      .catch((err) => console.error('저널 날짜 로드 실패', err))
  }, [])

  // 마운트 시 초안 복원 알림 (오늘일 때만)
  useEffect(() => {
    if (!isToday) return
    const saved = localStorage.getItem(JOURNAL_DRAFT_KEY)
    if (saved && normalize(saved) !== normalize(defaultContent)) {
      toast.info('이전 초안을 복원했습니다.')
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 오늘의 다이제스트 로드 (오늘일 때만)
  useEffect(() => {
    if (!isToday) return
    fetchDigest()
      .then(setDigest)
      .catch((err) => console.error('다이제스트 로드 실패', err))
  }, [isToday])

  // 과거 날짜 선택 시 저널 로드
  useEffect(() => {
    if (isToday) {
      const saved = localStorage.getItem(JOURNAL_DRAFT_KEY)
      setMarkdownContent(saved && saved.trim() ? saved : defaultContent)
      setEditorMode('wysiwyg')
      return
    }
    setIsLoadingHistory(true)
    fetchJournalsByDate(selectedDate)
      .then((entries) => {
        if (entries.length > 0) {
          setMarkdownContent(entries[0].content)
          setEditorMode('viewer')
        } else {
          setMarkdownContent(`*${formatDateKo(selectedDate)}에 작성된 저널이 없습니다.*`)
          setEditorMode('viewer')
        }
      })
      .catch((err) => {
        console.error('저널 로드 실패', err)
        toast.error('저널을 불러오지 못했습니다.')
      })
      .finally(() => setIsLoadingHistory(false))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedDate])

  // 다이제스트 로드 시 회고 질문 자동 생성
  useEffect(() => {
    if (!digest || digest.memories.length === 0) return
    const summary = digest.memories
      .map((m) => `[${m.type}] ${m.title}: ${m.summary}`)
      .join('\n')
    setIsLoadingStarter(true)
    fetchReviewQuestions(summary)
      .then((res) => setStarterQuestions(res.questions || []))
      .catch(() => {})
      .finally(() => setIsLoadingStarter(false))
  }, [digest])

  const loadRelatedMemories = useCallback(async (text: string) => {
    if (!text || text.trim().length < MIN_CONTENT_LENGTH_FOR_RELATED) {
      setRelatedMemories([])
      return
    }
    setIsLoadingRelated(true)
    try {
      const data = await fetchRelatedMemoriesApi(text)
      setRelatedMemories(data.memories || [])
    } catch (e) {
      console.error('관련 메모리 검색 실패', e)
    } finally {
      setIsLoadingRelated(false)
    }
  }, [])

  // 템플릿 선택 시 에디터 내용 교체
  const handleTemplateSelect = useCallback(
    (content: string) => {
      setMarkdownContent(content)
      syncContentToEditor(content, editorMode, editorRef)
    },
    [editorMode],
  )

  // 회고 질문 클릭 시 에디터에 삽입
  const handleStarterQuestion = useCallback(
    (question: string) => {
      const content = `# ${todayLabel} 회고\n\n> Q: ${question}\n\n`
      setMarkdownContent(content)
      syncContentToEditor(content, editorMode, editorRef)
    },
    [todayLabel, editorMode],
  )

  // AI에게 질문받기 (수동 트리거)
  const handleAskAI = useCallback(async () => {
    const context = digest?.memories.length
      ? digest.memories.map((m) => `[${m.type}] ${m.title}: ${m.summary}`).join('\n')
      : '오늘 하루를 돌아보며 회고를 시작하려 합니다.'
    setIsLoadingStarter(true)
    try {
      const res = await fetchReviewQuestions(context)
      setStarterQuestions(res.questions || [])
    } catch {
      toast.error('질문 생성에 실패했습니다.')
    } finally {
      setIsLoadingStarter(false)
    }
  }, [digest, toast])

  // 글 내용 변경 시 관련 메모리를 디바운스로 검색
  useEffect(() => {
    const timer = setTimeout(() => loadRelatedMemories(markdownContent), RELATED_MEMORIES_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [markdownContent, loadRelatedMemories])


  // WYSIWYG에서 HTML 변경 시 → 마크다운 동기화
  const handleWysiwygUpdate = useCallback((html: string) => {
    const md = turndown.turndown(html)
    setMarkdownContent(md)
  }, [])

  // 에디터 모드 전환 시 콘텐츠 포맷 동기화
  const handleModeChange = useCallback((newMode: EditorMode) => {
    if (newMode === editorMode) return

    if (editorMode === 'wysiwyg' && editorRef.current) {
      const html = editorRef.current.getHTML()
      const md = turndown.turndown(html)
      setMarkdownContent(md)
    }

    if (newMode === 'wysiwyg' && editorRef.current) {
      const html = markdownToHtml(markdownContent)
      editorRef.current.setContent(html)
    }

    setEditorMode(newMode)
  }, [editorMode, markdownContent])

  const handleMarkdownChange = useCallback((md: string) => {
    setMarkdownContent(md)
  }, [])

  // 메모리 카드 클릭 → 에디터에 블록 삽입
  const handleInsertMemory = useCallback((memory: DigestMemory | RelatedMemory) => {
    if (editorMode === 'wysiwyg' && editorRef.current) {
      editorRef.current.insertMemoryBlock({
        memoryId: memory.id,
        title: memory.title,
        summary: memory.summary,
        type: memory.type,
      })
    } else {
      const block = `\n> **[${memory.type}]** ${memory.title}\n> ${memory.summary}\n\n`
      setMarkdownContent((prev) => prev + block)
    }
  }, [editorMode])

  // 메모리 카드 클릭 → 상세 모달 열기
  const handleMemoryCardClick = useCallback((memoryId: string) => {
    setSelectedMemoryId(memoryId)
  }, [])

  // AI 성찰 질문 → 에디터에 삽입
  const handleInsertQuestion = useCallback((question: string) => {
    if (editorMode === 'wysiwyg' && editorRef.current) {
      editorRef.current.setContent(
        editorRef.current.getHTML() + `<blockquote><p>Q: ${question}</p></blockquote><p></p>`,
      )
    } else {
      setMarkdownContent((prev) => prev + `\n> Q: ${question}\n\n`)
    }
  }, [editorMode])

  // 드래그 앤 드롭 메모리 삽입
  const handleEditorDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    try {
      const data = JSON.parse(e.dataTransfer.getData('application/json'))
      handleInsertMemory(data)
    } catch {
      // 드래그 데이터가 아닌 경우 무시
    }
  }, [handleInsertMemory])

  const handleSave = async () => {
    if (!markdownContent.trim()) return
    setIsSaving(true)
    try {
      const memoryIds = extractMemoryIds()
      await saveJournal(markdownContent, memoryIds)
      localStorage.removeItem(JOURNAL_DRAFT_KEY)
      markSaved()
      toast.success('저장되었습니다!')
    } catch (e) {
      console.error('저널 저장 실패', e)
      toast.error( '저장에 실패했습니다.')
    } finally {
      setIsSaving(false)
    }
  }

  // 하루 정리: 채팅 세션 기반 초안 → 실패 시 메모리 기반 템플릿 폴백
  const handleDailySummary = async () => {
    if (!digest || digest.memories.length === 0) {
      toast.error( '오늘 수집된 메모리가 없습니다.')
      return
    }
    setIsGenerating(true)
    try {
      // 채팅 세션 기반 초안 시도
      try {
        const sessionList = await fetchChatSessions()
        if (sessionList.length > 0) {
          const result = await generateJournalDraft(sessionList[0].id)
          setMarkdownContent(result.draft)
          syncContentToEditor(result.draft, editorMode, editorRef)
          toast.success( '하루 정리 초안이 생성되었습니다!')
          return
        }
      } catch {
        // 채팅 세션 기반 실패 시 아래 메모리 기반 템플릿으로 폴백
      }

      // 메모리 기반 템플릿 폴백
      const template = `# ${todayLabel} 회고\n\n## 오늘의 메모리\n\n${digest.memories
        .map((m) => `- **[${m.type}]** ${m.title}: ${m.summary}`)
        .join('\n')}\n\n## 하루를 돌아보며\n\n`
      setMarkdownContent(template)
      syncContentToEditor(template, editorMode, editorRef)
      toast.success( '메모리 기반 템플릿이 생성되었습니다.')
    } finally {
      setIsGenerating(false)
    }
  }

  // 세션 목록을 불러와 선택 모달 표시
  const handleSessionDraft = async () => {
    setIsGenerating(true)
    try {
      const sessionList = await fetchChatSessions()
      if (sessionList.length === 0) {
        toast.error( '대화 세션이 없습니다. 먼저 Evening 모드로 대화해보세요.')
        return
      }
      setSessions(sessionList)
      setShowSessionPicker(true)
    } catch (e) {
      console.error('세션 목록 로드 실패', e)
      toast.error( '세션 목록을 불러오지 못했습니다.')
    } finally {
      setIsGenerating(false)
    }
  }

  const handleSelectSession = async (selectedSessionId: string) => {
    setShowSessionPicker(false)
    setIsGenerating(true)
    try {
      const result = await generateJournalDraft(selectedSessionId)
      setMarkdownContent(result.draft)
      syncContentToEditor(result.draft, editorMode, editorRef)
      toast.success( 'AI 초안이 생성되었습니다!')
    } catch (e) {
      console.error('초안 생성 실패', e)
      toast.error( '초안 생성에 실패했습니다.')
    } finally {
      setIsGenerating(false)
    }
  }

  // Tiptap 에디터 마운트 시 ref로 Editor 인스턴스 획득
  const handleEditorRef = useCallback((handle: TiptapEditorHandle | null) => {
    if (handle) {
      (editorRef as React.MutableRefObject<TiptapEditorHandle | null>).current = handle
    }
  }, [])

  const journalViewClass = [
    'journal-view',
    isMobile ? 'journal-view--mobile' : '',
    !isMobile && leftCollapsed && isToday ? 'journal-view--left-collapsed' : '',
    !isMobile && rightCollapsed && isToday ? 'journal-view--right-collapsed' : '',
  ].filter(Boolean).join(' ')

  return (
    <div className={journalViewClass}>
      {/* 모바일 탭 바 */}
      {isMobile && (
        <div className="journal-mobile-tabs">
          <button className={`journal-mobile-tab ${mobileTab === 'editor' ? 'active' : ''}`} onClick={() => setMobileTab('editor')}>에디터</button>
          <button className={`journal-mobile-tab ${mobileTab === 'memories' ? 'active' : ''}`} onClick={() => setMobileTab('memories')}>메모리</button>
          <button className={`journal-mobile-tab ${mobileTab === 'ai' ? 'active' : ''}`} onClick={() => setMobileTab('ai')}>AI 도우미</button>
        </div>
      )}

      {/* 메모리 사이드바 (좌측 패널, 오늘일 때만) */}
      {isToday && (
        <div className={isMobile && mobileTab !== 'memories' ? 'journal-panel--hidden' : ''}>
          <MemorySidebar
            todayMemories={digest?.memories ?? []}
            relatedMemories={relatedMemories}
            isLoadingRelated={isLoadingRelated}
            onInsertMemory={handleInsertMemory}
            onCardClick={handleMemoryCardClick}
            onDailySummary={handleDailySummary}
            onSessionDraft={handleSessionDraft}
            isGenerating={isGenerating}
            collapsed={isMobile ? false : leftCollapsed}
            onToggleCollapse={() => setLeftCollapsed(!leftCollapsed)}
          />
        </div>
      )}

      <div className={`journal-editor-section ${isMobile && mobileTab !== 'editor' ? 'journal-panel--hidden' : ''}`}>
        {/* 에디터 헤더 */}
        <div className="journal-editor-header">
          {isToday && (
            <button
              className="journal-panel-toggle journal-panel-toggle--left"
              onClick={() => setLeftCollapsed(!leftCollapsed)}
              title={leftCollapsed ? '메모리 사이드바 열기' : '메모리 사이드바 닫기'}
              type="button"
            >
              {leftCollapsed ? <PanelLeftOpen size={18} /> : <PanelLeftClose size={18} />}
            </button>
          )}
          <JournalDateNav
            currentDate={selectedDate}
            todayStr={todayStr}
            isToday={isToday}
            onDateChange={setSelectedDate}
            onToggleDatePicker={() => setShowDatePicker(!showDatePicker)}
          />
          <div className="journal-editor-actions">
            {isToday && autoSaveStatus === 'saved' && (
              <span className="journal-autosave-status">
                <Check size={14} />
                저장됨
              </span>
            )}
            {isToday && autoSaveStatus === 'saving' && (
              <span className="journal-autosave-status journal-autosave-status--saving">
                <Loader2 size={14} className="spin" />
                저장 중...
              </span>
            )}
            {isToday && (
              <button
                className="journal-save-btn"
                onClick={handleSave}
                disabled={isSaving}
                type="button"
              >
                <Save size={16} />
                {isSaving ? '저장 중...' : '저장'}
              </button>
            )}
            {isToday && (
              <button
                className="journal-panel-toggle journal-panel-toggle--right"
                onClick={() => setRightCollapsed(!rightCollapsed)}
                title={rightCollapsed ? 'AI 패널 열기' : 'AI 패널 닫기'}
                type="button"
              >
                {rightCollapsed ? <PanelRightOpen size={18} /> : <PanelRightClose size={18} />}
              </button>
            )}
          </div>
        </div>

        {/* 날짜 선택 드롭다운 */}
        {showDatePicker && journalDates.length > 0 && (
          <div className="journal-date-picker">
            <div className="journal-date-picker__list">
              {journalDates.map((d) => (
                <button
                  key={d.date}
                  className={`journal-date-picker__item ${d.date === selectedDate ? 'active' : ''}`}
                  onClick={() => { setSelectedDate(d.date); setShowDatePicker(false) }}
                  type="button"
                >
                  <span className="journal-date-picker__date">{formatDateKo(d.date)}</span>
                  <span className="journal-date-picker__meta">
                    {d.count}개 {d.mood === 'POSITIVE' ? '😊' : d.mood === 'NEGATIVE' ? '😔' : '📝'}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 툴바 (오늘일 때만) */}
        {isToday && (
          <EditorToolbar
            editor={tiptapEditor}
            mode={editorMode}
            onModeChange={handleModeChange}
          />
        )}

        {/* 히스토리 로딩 */}
        {isLoadingHistory && (
          <div className="journal-history-loading">
            <Loader2 size={20} className="spin" />
            저널 불러오는 중...
          </div>
        )}

        {/* 시작 도우미 (오늘일 때만) */}
        {showStarter && (
          <JournalStarter
            templates={templates}
            starterQuestions={starterQuestions}
            isLoadingStarter={isLoadingStarter}
            onSelectTemplate={handleTemplateSelect}
            onStarterQuestion={handleStarterQuestion}
            onAskAI={handleAskAI}
          />
        )}

        {/* 에디터 영역 */}
        <div
          className="journal-editor-area"
          onDrop={handleEditorDrop}
          onDragOver={(e) => e.preventDefault()}
        >
          {editorMode === 'wysiwyg' && (
            <>
              <TiptapEditor
                ref={handleEditorRef}
                initialContent={markdownToHtml(markdownContent)}
                onUpdate={handleWysiwygUpdate}
                onEditorReady={setTiptapEditor}
                editable
              />
              {tiptapEditor && <AIBubbleMenu editor={tiptapEditor} />}
            </>
          )}
          {editorMode === 'markdown' && (
            <MarkdownEditor
              content={markdownContent}
              onChange={handleMarkdownChange}
            />
          )}
          {editorMode === 'viewer' && (
            <ReadOnlyViewer content={markdownContent} />
          )}
        </div>

        </div>

      {/* 우측 패널: AI 분석 + Socrates (오늘일 때만) */}
      {isToday && (
        <div className={`journal-right-panel ${isMobile && mobileTab !== 'ai' ? 'journal-panel--hidden' : ''} ${!isMobile && rightCollapsed ? 'journal-right-panel--collapsed' : ''}`}>
          <div className="journal-right-panel__tabs">
            <button
              className={`journal-right-panel__tab ${rightTab === 'analysis' ? 'active' : ''}`}
              onClick={() => setRightTab('analysis')}
              type="button"
            >
              <Brain size={14} />
              AI 분석
            </button>
            <button
              className={`journal-right-panel__tab ${rightTab === 'socrates' ? 'active' : ''}`}
              onClick={() => setRightTab('socrates')}
              type="button"
            >
              <Bot size={14} />
              Socrates
            </button>
          </div>
          <div className="journal-right-panel__content">
            {rightTab === 'analysis' ? (
              <AIPanel
                content={markdownContent}
                onInsertQuestion={handleInsertQuestion}
              />
            ) : (
              <SocratesChatPanel
                chat={socratesChat}
                className="socrates-chat-panel--panel"
              />
            )}
          </div>
        </div>
      )}

      {/* 세션 선택 모달 */}
      {showSessionPicker && (
        <SessionPickerModal
          sessions={sessions}
          onSelect={handleSelectSession}
          onClose={() => setShowSessionPicker(false)}
        />
      )}

      {/* 메모리 상세 모달 */}
      {selectedMemoryId && (
        <MemoryDetailModal
          memoryId={selectedMemoryId}
          onClose={() => setSelectedMemoryId(null)}
          onDeleted={() => setSelectedMemoryId(null)}
        />
      )}
    </div>
  )
}
