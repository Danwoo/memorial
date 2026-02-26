import { useState, useEffect, useCallback } from 'react'
import { X, Pencil, BookOpen, Lightbulb, Loader2 } from 'lucide-react'
import type { DigestData, DailyInsight } from '../../types'
import type { DiaryEntry } from '../../types/diary'
import { fetchDigestByDate, fetchDiariesByDate } from '../../api'
import { useIsMobile } from '../../hooks/useMediaQuery'
import './DayDetailPanel.css'

interface DayDetailPanelProps {
  date: string
  onClose: () => void
  onNavigateJournal: (date: string) => void
  onNavigateMemory: (memoryId: string) => void
  dailyInsights: DailyInsight[]
  onInsightClick: (path: string) => void
}

function getMoodDot(mood: string | null): string {
  switch (mood) {
    case 'POSITIVE': return 'var(--color-success)'
    case 'NEGATIVE': return 'var(--color-error)'
    case 'MIXED': return 'var(--color-warning)'
    default: return 'var(--accent-primary)'
  }
}

function formatDateHeader(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  const weekdays = ['일', '월', '화', '수', '목', '금', '토']
  return `${d.getMonth() + 1}월 ${d.getDate()}일 ${weekdays[d.getDay()]}요일`
}

function isToday(dateStr: string): boolean {
  return dateStr === new Date().toISOString().slice(0, 10)
}

export default function DayDetailPanel({
  date, onClose, onNavigateJournal, onNavigateMemory,
  dailyInsights, onInsightClick,
}: DayDetailPanelProps) {
  const isMobile = useIsMobile()
  const [digest, setDigest] = useState<DigestData | null>(null)
  const [diaries, setDiaries] = useState<DiaryEntry[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let cancelled = false
    setLoading(true)

    Promise.all([
      fetchDigestByDate(date).catch(() => null),
      fetchDiariesByDate(date).catch(() => []),
    ]).then(([digestData, journalData]) => {
      if (cancelled) return
      setDigest(digestData)
      setDiaries(journalData)
      setLoading(false)
    })

    return () => { cancelled = true }
  }, [date])

  // ESC 키로 닫기
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleBackdropClick = useCallback(() => {
    onClose()
  }, [onClose])

  const scrapCount = digest?.summary.scrap_count ?? 0
  const diaryCount = diaries.length
  const scraps = digest?.scraps ?? []
  const showInsights = isToday(date) && dailyInsights.length > 0
  const isEmpty = !loading && diaryCount === 0 && scrapCount === 0

  return (
    <>
      {isMobile && <div className="day-panel__backdrop" onClick={handleBackdropClick} />}
      <div className={`day-panel ${isMobile ? 'day-panel--mobile' : 'day-panel--desktop'}`}>
        {/* 헤더 */}
        <div className="day-panel__header">
          <h3 className="day-panel__date">{formatDateHeader(date)}</h3>
          <button className="day-panel__close" onClick={onClose} aria-label="닫기" type="button">
            <X size={18} />
          </button>
        </div>

        {loading ? (
          <div className="day-panel__loading">
            <Loader2 size={24} className="spinning" />
          </div>
        ) : isEmpty ? (
          <div className="day-panel__empty">
            <p>이 날은 기록이 없어요</p>
            <button
              className="day-panel__cta"
              onClick={() => onNavigateJournal(date)}
              type="button"
            >
              <Pencil size={16} />
              다이어리 쓰기
            </button>
          </div>
        ) : (
          <div className="day-panel__body">
            {/* 요약 */}
            <div className="day-panel__summary">
              {diaryCount > 0 && (
                <span className="day-panel__summary-item">
                  <Pencil size={14} /> 다이어리 {diaryCount}개
                </span>
              )}
              {scrapCount > 0 && (
                <span className="day-panel__summary-item">
                  <BookOpen size={14} /> 스크랩 {scrapCount}개
                </span>
              )}
            </div>

            {/* 다이어리 목록 */}
            {diaries.length > 0 && (
              <div className="day-panel__section">
                <h4 className="day-panel__section-title">다이어리</h4>
                <div className="day-panel__list">
                  {diaries.map(j => (
                    <button
                      key={j.id}
                      className="day-panel__item"
                      onClick={() => onNavigateJournal(date)}
                      type="button"
                    >
                      <span
                        className="day-panel__mood-dot"
                        style={{ backgroundColor: getMoodDot(j.mood) }}
                      />
                      <span className="day-panel__item-text">
                        {j.content.slice(0, 60).replace(/<[^>]*>/g, '')}
                        {j.content.length > 60 ? '...' : ''}
                      </span>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 스크랩 목록 */}
            {scraps.length > 0 && (
              <div className="day-panel__section">
                <h4 className="day-panel__section-title">스크랩</h4>
                <div className="day-panel__list">
                  {scraps.map(m => (
                    <button
                      key={m.id}
                      className="day-panel__item"
                      onClick={() => onNavigateMemory(m.id)}
                      type="button"
                    >
                      <span className="day-panel__source-type">{m.type}</span>
                      <div className="day-panel__item-body">
                        <span className="day-panel__item-text">{m.title}</span>
                        {m.tags.length > 0 && (
                          <div className="day-panel__tags">
                            {m.tags.slice(0, 3).map(tag => (
                              <span key={tag} className="day-panel__tag">{tag}</span>
                            ))}
                          </div>
                        )}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* AI 인사이트 (오늘만) */}
            {showInsights && (
              <div className="day-panel__section">
                <h4 className="day-panel__section-title">
                  <Lightbulb size={14} /> AI 인사이트
                </h4>
                <div className="day-panel__list">
                  {dailyInsights.map((insight, i) => (
                    <button
                      key={i}
                      className="day-panel__insight"
                      onClick={() => onInsightClick(insight.cta_path)}
                      type="button"
                    >
                      <div className="day-panel__insight-title">{insight.title}</div>
                      <div className="day-panel__insight-desc">{insight.description}</div>
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* 하단 CTA */}
            <div className="day-panel__footer">
              <button
                className="day-panel__cta"
                onClick={() => onNavigateJournal(date)}
                type="button"
              >
                <Pencil size={16} />
                다이어리 쓰기
              </button>
            </div>
          </div>
        )}
      </div>
    </>
  )
}
