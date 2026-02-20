import { useState, useEffect } from 'react'

const JOURNAL_DRAFT_KEY = 'memoir-journal-draft'
const AUTOSAVE_DEBOUNCE_MS = 2000
const SERVER_AUTOSAVE_MS = 5000

// 공백 정규화 헬퍼
const normalize = (s: string) => s.replace(/\s+/g, ' ').trim()

export type AutoSaveStatus = '' | 'saving' | 'saved'

export function useJournalAutosave(
  markdownContent: string,
  defaultContent: string,
  isToday: boolean,
  extractMemoryIds: () => string[],
  serverSave: (content: string, memoryIds: string[]) => Promise<unknown>,
) {
  const [autoSaveStatus, setAutoSaveStatus] = useState<AutoSaveStatus>('')

  // localStorage 디바운스 저장
  useEffect(() => {
    if (!isToday) return
    if (normalize(markdownContent) === normalize(defaultContent)) return
    const timer = setTimeout(() => {
      localStorage.setItem(JOURNAL_DRAFT_KEY, markdownContent)
    }, AUTOSAVE_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [markdownContent, defaultContent, isToday])

  // 서버 자동 저장 (언마운트/deps 변경 시 상태 갱신 방지)
  useEffect(() => {
    if (!isToday) return
    if (normalize(markdownContent) === normalize(defaultContent)) return
    let cancelled = false
    const timer = setTimeout(async () => {
      setAutoSaveStatus('saving')
      try {
        const memoryIds = extractMemoryIds()
        await serverSave(markdownContent, memoryIds)
        if (!cancelled) {
          setAutoSaveStatus('saved')
          setTimeout(() => { if (!cancelled) setAutoSaveStatus('') }, 3000)
        }
      } catch (e) {
        console.error('자동 저장 실패', e)
        if (!cancelled) setAutoSaveStatus('')
      }
    }, SERVER_AUTOSAVE_MS)
    return () => { cancelled = true; clearTimeout(timer) }
  }, [markdownContent, defaultContent, isToday, extractMemoryIds, serverSave])

  return { autoSaveStatus, JOURNAL_DRAFT_KEY }
}
