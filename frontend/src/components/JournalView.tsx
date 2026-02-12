import { useState, useEffect, useCallback, useRef } from 'react'
import { Save } from 'lucide-react'
import TurndownService from 'turndown'
import type { EditorMode, RelatedMemory, DigestMemory, DigestData, ChatSessionResponse } from '../types'
import {
  saveJournal,
  fetchRelatedMemories as fetchRelatedMemoriesApi,
  generateJournalDraft,
  fetchChatSessions,
  fetchDigest,
} from '../api'
import type { Editor } from '@tiptap/react'
import { TiptapEditor, type TiptapEditorHandle } from './journal/TiptapEditor'
import { EditorToolbar } from './journal/EditorToolbar'
import { MarkdownEditor } from './journal/MarkdownEditor'
import { ReadOnlyViewer } from './journal/ReadOnlyViewer'
import { MemorySidebar } from './journal/MemorySidebar'
import { AIBubbleMenu } from './journal/AIBubbleMenu'
import { AIPanel } from './journal/AIPanel'
import { SessionPickerModal } from './journal/SessionPickerModal'
import './JournalView.css'

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

// 간이 마크다운 → HTML 변환 (StarterKit 범위)
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
    .replace(/(<li>.*<\/li>\n?)+/g, (match) => `<ul>${match}</ul>`)
    .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
    .replace(/^(?!<[hubloas]|<hr|<li|<blockquote)(.+)$/gm, '<p>$1</p>')
    .replace(/<\/blockquote>\s*<blockquote>/g, '\n')
}

export default function JournalView() {
  const today = new Date().toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
  const editorRef = useRef<TiptapEditorHandle>(null)

  const [markdownContent, setMarkdownContent] = useState(`# ${today} 회고\n\n오늘은...\n\n`)
  const [editorMode, setEditorMode] = useState<EditorMode>('wysiwyg')
  const [digest, setDigest] = useState<DigestData | null>(null)
  const [relatedMemories, setRelatedMemories] = useState<RelatedMemory[]>([])
  const [isLoadingRelated, setIsLoadingRelated] = useState(false)
  const [isSaving, setIsSaving] = useState(false)
  const [saveStatus, setSaveStatus] = useState<{ type: 'success' | 'error'; message: string } | null>(null)
  const [isGenerating, setIsGenerating] = useState(false)
  const [sessions, setSessions] = useState<ChatSessionResponse[]>([])
  const [showSessionPicker, setShowSessionPicker] = useState(false)

  const [tiptapEditor, setTiptapEditor] = useState<Editor | null>(null)

  // 마운트 시 오늘의 다이제스트 로드
  useEffect(() => {
    fetchDigest()
      .then(setDigest)
      .catch((err) => console.error('다이제스트 로드 실패', err))
  }, [])

  // 관련 메모리 1.5초 디바운스
  const loadRelatedMemories = useCallback(async (text: string) => {
    if (!text || text.trim().length < 20) {
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

  useEffect(() => {
    const timer = setTimeout(() => loadRelatedMemories(markdownContent), 1500)
    return () => clearTimeout(timer)
  }, [markdownContent, loadRelatedMemories])

  const showSaveStatus = (type: 'success' | 'error', message: string) => {
    setSaveStatus({ type, message })
    setTimeout(() => setSaveStatus(null), 3000)
  }

  // WYSIWYG에서 HTML 변경 시 → 마크다운 동기화
  const handleWysiwygUpdate = useCallback((html: string) => {
    const md = turndown.turndown(html)
    setMarkdownContent(md)
  }, [])

  // 모드 전환
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

  // 마크다운 에디터 변경
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

  // 저장
  const handleSave = async () => {
    if (!markdownContent.trim()) return
    setIsSaving(true)
    try {
      await saveJournal(markdownContent)
      showSaveStatus('success', '저장되었습니다!')
    } catch (e) {
      console.error(e)
      showSaveStatus('error', '저장에 실패했습니다.')
    } finally {
      setIsSaving(false)
    }
  }

  // 하루 정리 (다이제스트 기반 템플릿)
  const handleDailySummary = async () => {
    if (!digest || digest.memories.length === 0) {
      showSaveStatus('error', '오늘 수집된 메모리가 없습니다.')
      return
    }
    setIsGenerating(true)
    try {
      const sessionList = await fetchChatSessions()
      if (sessionList.length > 0) {
        const latest = sessionList[0]
        const result = await generateJournalDraft(latest.id)
        setMarkdownContent(result.draft)
        if (editorMode === 'wysiwyg' && editorRef.current) {
          editorRef.current.setContent(markdownToHtml(result.draft))
        }
        showSaveStatus('success', '하루 정리 초안이 생성되었습니다!')
        return
      }
    } catch {
      // 채팅 세션 기반 실패 시 폴백
    }

    // 메모리 기반 템플릿 폴백
    const template = `# ${today} 회고\n\n## 오늘의 메모리\n\n${digest.memories
      .map((m) => `- **[${m.type}]** ${m.title}: ${m.summary}`)
      .join('\n')}\n\n## 하루를 돌아보며\n\n`
    setMarkdownContent(template)
    if (editorMode === 'wysiwyg' && editorRef.current) {
      editorRef.current.setContent(markdownToHtml(template))
    }
    showSaveStatus('success', '메모리 기반 템플릿이 생성되었습니다.')
    setIsGenerating(false)
  }

  // 세션 기반 초안
  const handleSessionDraft = async () => {
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
      setMarkdownContent(result.draft)
      if (editorMode === 'wysiwyg' && editorRef.current) {
        editorRef.current.setContent(markdownToHtml(result.draft))
      }
      showSaveStatus('success', 'AI 초안이 생성되었습니다!')
    } catch (e) {
      console.error(e)
      showSaveStatus('error', '초안 생성에 실패했습니다.')
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

  return (
    <div className="journal-view">
      <div className="journal-editor-section">
        {/* 에디터 헤더 */}
        <div className="journal-editor-header">
          <h2>Today's Journal</h2>
          <div className="journal-editor-actions">
            {saveStatus && (
              <span className={`journal-save-status journal-save-status--${saveStatus.type}`}>
                {saveStatus.message}
              </span>
            )}
            <button
              className="journal-save-btn"
              onClick={handleSave}
              disabled={isSaving}
              type="button"
            >
              <Save size={16} />
              {isSaving ? '저장 중...' : '저장'}
            </button>
          </div>
        </div>

        {/* 툴바 */}
        <EditorToolbar
          editor={tiptapEditor}
          mode={editorMode}
          onModeChange={handleModeChange}
        />

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

        {/* AI 하단 패널 */}
        <AIPanel
          content={markdownContent}
          onInsertQuestion={handleInsertQuestion}
        />
      </div>

      {/* 메모리 사이드바 */}
      <MemorySidebar
        todayMemories={digest?.memories ?? []}
        relatedMemories={relatedMemories}
        isLoadingRelated={isLoadingRelated}
        onInsertMemory={handleInsertMemory}
        onDailySummary={handleDailySummary}
        onSessionDraft={handleSessionDraft}
        isGenerating={isGenerating}
      />

      {/* 세션 선택 모달 */}
      {showSessionPicker && (
        <SessionPickerModal
          sessions={sessions}
          onSelect={handleSelectSession}
          onClose={() => setShowSessionPicker(false)}
        />
      )}
    </div>
  )
}
