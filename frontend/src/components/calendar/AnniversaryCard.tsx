import { useMemo } from 'react'
import { Sparkles } from 'lucide-react'
import type { DiaryDateInfo } from '../../types/diary'
import './AnniversaryCard.css'

interface AnniversaryCardProps {
  journalDates: DiaryDateInfo[]
  onOpen: (date: string) => void
}

function oneYearAgoToday(): string {
  const now = new Date()
  // 윤년 안전화: 2/29 → year-1 시 JS Date가 3/1로 정규화하는 문제를 피하기 위해
  // 같은 월/일을 직접 조립하고, 해당 년도에 그 날이 없으면 마지막 날로 클램프.
  const y = now.getFullYear() - 1
  const m = now.getMonth()
  const day = now.getDate()
  const lastDayOfMonth = new Date(y, m + 1, 0).getDate()
  const safeDay = Math.min(day, lastDayOfMonth)
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(safeDay).padStart(2, '0')}`
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
