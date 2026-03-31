import { useState, useEffect, useCallback, useRef, useMemo } from 'react'
import { useResizePanel } from '../hooks/useResizePanel'
import { useLocation } from 'react-router-dom'
import { Save, Loader2, Check, PanelLeftClose, PanelRightClose, PanelLeftOpen, PanelRightOpen, Bot, Brain, Pencil } from 'lucide-react'
import { useToast } from '../contexts/ToastContext'
import { useIsMobile } from '../hooks/useMediaQuery'
import { useSocratesChat } from '../hooks/useSocratesChat'
import TurndownService from 'turndown'
import type { EditorMode, RelatedScrap, DigestScrap, DigestData, SocratesSessionResponse, DiaryDateInfo } from '../types'
import {
  saveDiary,
  updateDiary,
  fetchRelatedScraps as fetchRelatedScrapsApi,
  generateDiaryDraft,
  fetchSocratesSessions,
  fetchDigest,
  fetchReviewQuestions,
  fetchDiaryDates,
  fetchDiariesByDate,
  searchDiaries,
} from '../api'
import type { Editor } from '@tiptap/react'
import { TiptapEditor, type TiptapEditorHandle } from './journal/TiptapEditor'
import { EditorToolbar } from './journal/EditorToolbar'
import { MarkdownEditor } from './journal/MarkdownEditor'
import { ReadOnlyViewer } from './journal/ReadOnlyViewer'
import { MemorySidebar } from './journal/MemorySidebar'
import { AIBubbleMenu } from './journal/AIBubbleMenu'
import { AIPanel } from './journal/AIPanel'
import SocratesPanel from './socrates/SocratesPanel'
import { SessionPickerModal } from './journal/SessionPickerModal'
import { JournalDateNav } from './journal/JournalDateNav'
import { JournalStarter } from './journal/JournalStarter'
import { useJournalAutosave } from '../hooks/useJournalAutosave'
import ScrapDetailModal from './ScrapDetailModal'
import './DiaryView.css'

// 관련 스크랩 검색을 트리거하기 위한 최소 글자 수
const MIN_CONTENT_LENGTH_FOR_RELATED = 20

// 관련 스크랩 디바운스 지연 시간(ms)
const RELATED_SCRAPS_DEBOUNCE_MS = 800

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

export default function DiaryView() {
  const todayStr = useMemo(() => toDateStr(new Date()), [])
  const todayLabel = formatDateKo(todayStr)
  const editorRef = useRef<TiptapEditorHandle>(null)
  const toast = useToast()
  const location = useLocation()

  // 날짜 네비게이션
  const [selectedDate, setSelectedDate] = useState(todayStr)
  const [diaryDates, setDiaryDates] = useState<DiaryDateInfo[]>([])
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
  const [relatedScraps, setRelatedScraps] = useState<RelatedScrap[]>([])
  const [isLoadingRelatedScraps, setIsLoadingRelatedScraps] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [isGenerating, setIsGenerating] = useState(false)
  const [sessions, setSessions] = useState<SocratesSessionResponse[]>([])
  const [showSessionPicker, setShowSessionPicker] = useState(false)
  const [isLoadingHistory, setIsLoadingHistory] = useState(false)
  const [pastEntryId, setPastEntryId] = useState<string | null>(null)
  const [diarySearchOpen, setDiarySearchOpen] = useState(false)
  const [diarySearchQuery, setDiarySearchQuery] = useState('')
  const [diarySearchResults, setDiarySearchResults] = useState<Array<{ id: string; content: string; created_at: string }>>([])
  const [isSearching, setIsSearching] = useState(false)

  const [tiptapEditor, setTiptapEditor] = useState<Editor | null>(null)
  const [starterQuestions, setStarterQuestions] = useState<string[]>([])
  const [isLoadingStarter, setIsLoadingStarter] = useState(false)
  const [selectedScrapId, setSelectedScrapId] = useState<string | null>(null)

  // 우측 패널 탭 (AI 분석 / Socrates)
  const [rightTab, setRightTab] = useState<'analysis' | 'socrates'>('analysis')

  // Socrates 채팅 훅
  const socratesChat = useSocratesChat({
    mode: 'panel',
    context: { type: 'diary', content: markdownContent, title: `${selectedDate} 일기` },
    agentType: 'socrates',
  })

  // 모바일 탭 전환
  const isMobile = useIsMobile()
  const [mobileTab, setMobileTab] = useState<'editor' | 'memories' | 'ai'>('editor')

  // 패널 너비 (기본: 우측 = 좌측 2배)
  const { vw: leftVw, onMouseDown: onLeftResize } = useResizePanel(15, 8, 30, 'right', 'diary-left-panel-vw')
  const { vw: rightVw, onMouseDown: onRightResize } = useResizePanel(30, 15, 45, 'left', 'diary-right-panel-vw')

  // 좌/우 패널 collapse 상태
  const [leftCollapsed, setLeftCollapsed] = useState(() => {
    try {
      const saved = localStorage.getItem('memoir-diary-panels')
      return saved ? JSON.parse(saved).left ?? false : false
    } catch { return false }
  })
  const [rightCollapsed, setRightCollapsed] = useState(() => {
    try {
      const saved = localStorage.getItem('memoir-diary-panels')
      return saved ? JSON.parse(saved).right ?? false : false
    } catch { return false }
  })

  // collapse 상태 localStorage 저장
  useEffect(() => {
    localStorage.setItem('memoir-diary-panels', JSON.stringify({ left: leftCollapsed, right: rightCollapsed }))
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
    await saveDiary(content, memoryIds)
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
      openSocrates?: boolean
      topic?: string
      initialMessage?: string
      sourceContext?: import('../types').SourceContext
    } | null
    if (!state) return
    if (state.date) {
      setSelectedDate(state.date)
    }
    if (state.openSocrates) {
      setRightTab('socrates')
      setRightCollapsed(false)
      if (isMobile) setMobileTab('ai')
      if (state.sourceContext) {
        socratesChat.setSourceContextOverride(state.sourceContext as import('../hooks/useSocratesChat').SocratesChatContext)
      }
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
    fetchDiaryDates()
      .then((res) => setDiaryDates(res.dates))
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
      setPastEntryId(null)
      return
    }
    setIsLoadingHistory(true)
    setPastEntryId(null)
    fetchDiariesByDate(selectedDate)
      .then((entries) => {
        if (entries.length > 0) {
          setMarkdownContent(entries[0].content)
          setPastEntryId(entries[0].id ?? null)
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
    if (!digest || digest.scraps.length === 0) return
    const summary = digest.scraps
      .map((m) => `[${m.type}] ${m.title}: ${m.summary}`)
      .join('\n')
    setIsLoadingStarter(true)
    fetchReviewQuestions(summary)
      .then((res) => setStarterQuestions(res.questions || []))
      .catch(() => {})
      .finally(() => setIsLoadingStarter(false))
  }, [digest])

  const loadRelatedScraps = useCallback(async (text: string) => {
    if (!text || text.trim().length < MIN_CONTENT_LENGTH_FOR_RELATED) {
      setRelatedScraps([])
      return
    }
    setIsLoadingRelatedScraps(true)
    try {
      const data = await fetchRelatedScrapsApi(text)
      setRelatedScraps(data.scraps || [])
    } catch (e) {
      console.error('관련 스크랩 검색 실패', e)
    } finally {
      setIsLoadingRelatedScraps(false)
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
    const context = digest?.scraps.length
      ? digest.scraps.map((m) => `[${m.type}] ${m.title}: ${m.summary}`).join('\n')
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
    const timer = setTimeout(() => loadRelatedScraps(markdownContent), RELATED_SCRAPS_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [markdownContent, loadRelatedScraps])


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
  const handleInsertScrap = useCallback((memory: DigestScrap | RelatedScrap) => {
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

  // 스크랩 카드 클릭 → 상세 모달 열기
  const handleScrapCardClick = useCallback((scrapId: string) => {
    setSelectedScrapId(scrapId)
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

  // 소크라테스 대화 내용 → 에디터에 인용 블록 삽입
  const handleInsertFromSocrates = useCallback((content: string) => {
    const escaped = content.replace(/</g, '&lt;').replace(/>/g, '&gt;')
    if (editorMode === 'wysiwyg' && editorRef.current) {
      editorRef.current.setContent(
        editorRef.current.getHTML() + `<blockquote><p>${escaped}</p><p><em>— Socrates 대화에서</em></p></blockquote><p></p>`,
      )
    } else {
      const quoted = content.split('\n').map(line => `> ${line}`).join('\n')
      setMarkdownContent((prev) => prev + `\n${quoted}\n> *— Socrates 대화에서*\n\n`)
    }
    toast.success('일기에 삽입했습니다')
  }, [editorMode, toast])

  // 드래그 앤 드롭 메모리 삽입
  const handleEditorDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    try {
      const data = JSON.parse(e.dataTransfer.getData('application/json'))
      handleInsertScrap(data)
    } catch {
      // 드래그 데이터가 아닌 경우 무시
    }
  }, [handleInsertScrap])

  const handleSave = async () => {
    if (!markdownContent.trim()) return
    setIsSaving(true)
    try {
      const memoryIds = extractMemoryIds()
      if (pastEntryId && !isToday) {
        await updateDiary(pastEntryId, markdownContent, memoryIds)
      } else {
        await saveDiary(markdownContent, memoryIds)
        localStorage.removeItem(JOURNAL_DRAFT_KEY)
      }
      markSaved()
      toast.success('저장되었습니다!')
    } catch (e) {
      console.error('저널 저장 실패', e)
      toast.error('저장에 실패했습니다.')
    } finally {
      setIsSaving(false)
    }
  }

  // 다이어리 검색 디바운스
  useEffect(() => {
    if (!diarySearchQuery.trim()) {
      setDiarySearchResults([])
      return
    }
    setIsSearching(true)
    const timer = setTimeout(() => {
      searchDiaries(diarySearchQuery.trim())
        .then(results => setDiarySearchResults(results))
        .catch(() => setDiarySearchResults([]))
        .finally(() => setIsSearching(false))
    }, 400)
    return () => clearTimeout(timer)
  }, [diarySearchQuery])

  // Ctrl+S / Ctrl+[ / Ctrl+] 키보드 단축키
  const handleSaveRef = useRef(handleSave)
  handleSaveRef.current = handleSave
  const selectedDateRef = useRef(selectedDate)
  selectedDateRef.current = selectedDate
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === 's') {
        e.preventDefault()
        handleSaveRef.current()
      } else if ((e.metaKey || e.ctrlKey) && e.key === '[') {
        e.preventDefault()
        const d = new Date(selectedDateRef.current + 'T00:00:00')
        d.setDate(d.getDate() - 1)
        const prev = d.toISOString().slice(0, 10)
        if (prev >= '2020-01-01') setSelectedDate(prev)
      } else if ((e.metaKey || e.ctrlKey) && e.key === ']') {
        e.preventDefault()
        const d = new Date(selectedDateRef.current + 'T00:00:00')
        d.setDate(d.getDate() + 1)
        const next = d.toISOString().slice(0, 10)
        if (next <= todayStr) setSelectedDate(next)
      }
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [todayStr, setSelectedDate])

  // 하루 정리: 채팅 세션 기반 초안 → 실패 시 메모리 기반 템플릿 폴백
  const handleDailySummary = async () => {
    if (!digest || digest.scraps.length === 0) {
      toast.error( '오늘 수집된 스크랩이 없습니다.')
      return
    }
    setIsGenerating(true)
    try {
      // 채팅 세션 기반 초안 시도
      try {
        const sessionList = await fetchSocratesSessions()
        if (sessionList.length > 0) {
          const result = await generateDiaryDraft(sessionList[0].id)
          setMarkdownContent(result.draft)
          syncContentToEditor(result.draft, editorMode, editorRef)
          toast.success( '하루 정리 초안이 생성되었습니다!')
          return
        }
      } catch {
        // 채팅 세션 기반 실패 시 아래 메모리 기반 템플릿으로 폴백
      }

      // 메모리 기반 템플릿 폴백
      const template = `# ${todayLabel} 회고\n\n## 오늘의 스크랩\n\n${digest.scraps
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
      const sessionList = await fetchSocratesSessions()
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
      const result = await generateDiaryDraft(selectedSessionId)
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
    'diary-view',
    isMobile ? 'diary-view--mobile' : '',
  ].filter(Boolean).join(' ')

  // 인라인 그리드 컬럼 (collapsed / today 상태 반영)
  const gridStyle = !isMobile ? {
    gridTemplateColumns: (() => {
      if (!isToday) return '1fr'
      const lw = leftCollapsed ? '0' : `${leftVw}vw`
      const rw = rightCollapsed ? '0' : `${rightVw}vw`
      return `${lw} 1fr ${rw}`
    })(),
  } : undefined

  return (
    <div className={journalViewClass} style={gridStyle}>
      {/* 모바일 탭 바 */}
      {isMobile && (
        <div className="diary-mobile-tabs">
          <button className={`diary-mobile-tab ${mobileTab === 'editor' ? 'active' : ''}`} onClick={() => setMobileTab('editor')}>에디터</button>
          <button className={`diary-mobile-tab ${mobileTab === 'memories' ? 'active' : ''}`} onClick={() => setMobileTab('memories')}>메모리</button>
          <button className={`diary-mobile-tab ${mobileTab === 'ai' ? 'active' : ''}`} onClick={() => setMobileTab('ai')}>AI 도우미</button>
        </div>
      )}

      {/* 메모리 사이드바 (좌측 패널, 오늘일 때만) */}
      {isToday && (
        <div className={`diary-left-panel-outer${isMobile && mobileTab !== 'memories' ? ' diary-panel--hidden' : ''}`}>
          {!isMobile && !leftCollapsed && (
            <div className="resize-handle resize-handle--right" onMouseDown={onLeftResize} />
          )}
          <MemorySidebar
            todayScraps={digest?.scraps ?? []}
            relatedScraps={relatedScraps}
            isLoadingRelatedScraps={isLoadingRelatedScraps}
            onInsertScrap={handleInsertScrap}
            onCardClick={handleScrapCardClick}
            onDailySummary={handleDailySummary}
            onSessionDraft={handleSessionDraft}
            isGenerating={isGenerating}
            collapsed={isMobile ? false : leftCollapsed}
            onToggleCollapse={() => setLeftCollapsed(!leftCollapsed)}
          />
        </div>
      )}

      <div className={`diary-editor-section ${isMobile && mobileTab !== 'editor' ? 'diary-panel--hidden' : ''}`}>
        {/* 에디터 헤더 */}
        <div className="diary-editor-header">
          {isToday && (
            <button
              className="diary-panel-toggle diary-panel-toggle--left"
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
            onToggleSearch={() => setDiarySearchOpen(!diarySearchOpen)}
            isSearchOpen={diarySearchOpen}
          />
          {diarySearchOpen && (
            <div className="diary-search-bar">
              <input
                className="diary-search-input"
                type="text"
                placeholder="다이어리 내용 검색..."
                value={diarySearchQuery}
                onChange={e => setDiarySearchQuery(e.target.value)}
                autoFocus
              />
              {isSearching && <Loader2 size={14} className="spin" />}
              {diarySearchResults.length > 0 && (
                <div className="diary-search-results" role="listbox" aria-label="다이어리 검색 결과" aria-live="polite">
                  {diarySearchResults.slice(0, 10).map(r => (
                    <button
                      key={r.id}
                      className="diary-search-result-item"
                      onClick={() => {
                        const dateStr = r.created_at.slice(0, 10)
                        setSelectedDate(dateStr)
                        setDiarySearchOpen(false)
                        setDiarySearchQuery('')
                      }}
                      type="button"
                    >
                      <span className="diary-search-result-date">{r.created_at.slice(0, 10)}</span>
                      <span className="diary-search-result-preview">
                        {r.content.replace(/<[^>]*>/g, '').slice(0, 80)}...
                      </span>
                    </button>
                  ))}
                </div>
              )}
              {diarySearchQuery && !isSearching && diarySearchResults.length === 0 && (
                <div className="diary-search-empty">검색 결과가 없습니다</div>
              )}
            </div>
          )}
          <div className="diary-editor-actions">
            {isToday && autoSaveStatus === 'saved' && (
              <span className="diary-autosave-status">
                <Check size={14} />
                저장됨
              </span>
            )}
            {isToday && autoSaveStatus === 'saving' && (
              <span className="diary-autosave-status diary-autosave-status--saving">
                <Loader2 size={14} className="spin" />
                저장 중...
              </span>
            )}
            {!isToday && pastEntryId && editorMode === 'viewer' && (
              <button
                className="diary-save-btn"
                onClick={() => setEditorMode('wysiwyg')}
                type="button"
              >
                <Pencil size={16} />
                편집
              </button>
            )}
            {(isToday || editorMode !== 'viewer') && (
              <button
                className="diary-save-btn"
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
                className="diary-panel-toggle diary-panel-toggle--right"
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
        {showDatePicker && diaryDates.length > 0 && (
          <div className="diary-date-picker">
            <div className="diary-date-picker__list">
              {diaryDates.map((d) => (
                <button
                  key={d.date}
                  className={`diary-date-picker__item ${d.date === selectedDate ? 'active' : ''}`}
                  onClick={() => { setSelectedDate(d.date); setShowDatePicker(false) }}
                  type="button"
                >
                  <span className="diary-date-picker__date">{formatDateKo(d.date)}</span>
                  <span className="diary-date-picker__meta">
                    {d.count}개 {d.mood === 'POSITIVE' ? '😊' : d.mood === 'NEGATIVE' ? '😔' : '📝'}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 툴바 */}
        <EditorToolbar
          editor={tiptapEditor}
          mode={editorMode}
          onModeChange={handleModeChange}
        />

        {/* 히스토리 로딩 */}
        {isLoadingHistory && (
          <div className="diary-history-loading">
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
          className="diary-editor-area"
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
        <div className={`diary-right-panel ${isMobile && mobileTab !== 'ai' ? 'diary-panel--hidden' : ''} ${!isMobile && rightCollapsed ? 'diary-right-panel--collapsed' : ''}`}>
          {!isMobile && !rightCollapsed && (
            <div className="resize-handle resize-handle--left" onMouseDown={onRightResize} />
          )}
          <div className="diary-right-panel__tabs">
            <button
              className={`diary-right-panel__tab ${rightTab === 'analysis' ? 'active' : ''}`}
              onClick={() => setRightTab('analysis')}
              type="button"
            >
              <Brain size={14} />
              AI 분석
            </button>
            <button
              className={`diary-right-panel__tab ${rightTab === 'socrates' ? 'active' : ''}`}
              onClick={() => setRightTab('socrates')}
              type="button"
            >
              <Bot size={14} />
              Socrates
            </button>
          </div>
          <div className="diary-right-panel__content">
            {rightTab === 'analysis' ? (
              <AIPanel
                content={markdownContent}
                onInsertQuestion={handleInsertQuestion}
              />
            ) : (
              <SocratesPanel
                chat={socratesChat}
                className="socrates-panel--panel"
                onScrapClick={setSelectedScrapId}
                onInsertToDiary={handleInsertFromSocrates}
                isPanelMode
                context={{ type: 'diary' }}
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

      {/* 스크랩 상세 모달 */}
      {selectedScrapId && (
        <ScrapDetailModal
          scrapId={selectedScrapId}
          onClose={() => setSelectedScrapId(null)}
          onDeleted={() => setSelectedScrapId(null)}
        />
      )}
    </div>
  )
}
