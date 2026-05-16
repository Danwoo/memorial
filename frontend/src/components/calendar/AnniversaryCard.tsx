import { useMemo } from 'react'
import { Sparkles } from 'lucide-react'
import type { DiaryDateInfo } from '../../types/diary'
import './AnniversaryCard.css'

interface AnniversaryCardProps {
  journalDates: DiaryDateInfo[]
  onOpen: (date: string) => void
}

function oneYearAgoToday(): string {
  const d = new Date()
  d.setFullYear(d.getFullYear() - 1)
  return d.toISOString().slice(0, 10)
}

function formatKoreanDate(dateStr: string): string {
  const [y, m, d] = dateStr.split('-')
  return `${y}년 ${parseInt(m, 10)}월 ${parseInt(d, 10)}일`
}

export default function AnniversaryCard({ journalDates, onOpen }: AnniversaryCardProps) {
  const target = oneYearAgoToday()
  const entry = useMemo(() => journalDates.find((d) => d.date === target), [journalDates, target])

  if (!entry) return null

  return (
    <button
      type="button"
      className="anniversary-card"
      onClick={() => onOpen(entry.date)}
    >
      <div className="anniversary-card__icon">
        <Sparkles size={14} />
      </div>
      <div className="anniversary-card__body">
        <div className="anniversary-card__header">
          <span className="anniversary-card__eyebrow">1년 전 오늘</span>
          <span className="anniversary-card__date">{formatKoreanDate(entry.date)}</span>
        </div>
        <div className="anniversary-card__meta">
          {entry.tags && entry.tags.length > 0 ? (
            <span className="anniversary-card__tags">
              {entry.tags.slice(0, 3).join(' · ')}
            </span>
          ) : (
            <span className="anniversary-card__tags">다이어리를 적었어요</span>
          )}
        </div>
      </div>
      <span className="anniversary-card__cta">다시 보기 →</span>
    </button>
  )
}
