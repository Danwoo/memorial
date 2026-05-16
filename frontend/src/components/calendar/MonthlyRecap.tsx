import { useMemo } from 'react'
import { PenLine, BookOpen } from 'lucide-react'
import type { ActivityData } from '../../types'
import type { DiaryDateInfo } from '../../types/diary'
import './MonthlyRecap.css'

interface MonthlyRecapProps {
  year: number
  month: number
  journalDates: DiaryDateInfo[]
  activityData: ActivityData[]
}

function buildOneLine(diaryDays: number, scrapCount: number, topTag: string | null): string | null {
  if (diaryDays === 0 && scrapCount === 0) return null
  if (topTag && (diaryDays + scrapCount) >= 5) {
    return `이번 달은 ${topTag} 관련 기록이 많았어요`
  }
  if (diaryDays >= 5) return '꾸준히 다이어리를 쓰고 있어요'
  if (scrapCount >= 10) return '많은 글과 자료를 모았어요'
  return null
}

export default function MonthlyRecap({ year, month, journalDates, activityData }: MonthlyRecapProps) {
  const monthPrefix = `${year}-${String(month + 1).padStart(2, '0')}`

  const stats = useMemo(() => {
    const monthDiary = journalDates.filter((d) => d.date.startsWith(monthPrefix))
    const monthActivity = activityData.filter((a) => a.date.startsWith(monthPrefix))

    const diaryDays = monthDiary.length
    const scrapCount = monthActivity.reduce((sum, a) => sum + (a.count ?? 0), 0)

    const tagCounts = new Map<string, number>()
    for (const d of monthDiary) {
      for (const t of d.tags ?? []) tagCounts.set(t, (tagCounts.get(t) ?? 0) + 1)
    }
    for (const a of monthActivity) {
      for (const t of a.tags ?? []) tagCounts.set(t, (tagCounts.get(t) ?? 0) + 1)
    }
    const topTags = [...tagCounts.entries()]
      .sort((a, b) => b[1] - a[1])
      .slice(0, 3)
      .map(([t]) => t)

    return { diaryDays, scrapCount, topTags }
  }, [journalDates, activityData, monthPrefix])

  if (stats.diaryDays === 0 && stats.scrapCount === 0) return null

  const oneLine = buildOneLine(stats.diaryDays, stats.scrapCount, stats.topTags[0] ?? null)

  return (
    <div className="monthly-recap">
      <div className="monthly-recap__stats">
        <span className="monthly-recap__period">이번 달</span>
        <div className="monthly-recap__stat">
          <PenLine size={13} className="monthly-recap__icon monthly-recap__icon--diary" />
          <span className="monthly-recap__value">
            <strong>{stats.diaryDays}</strong>
            <span className="monthly-recap__unit">일</span>
          </span>
          <span className="monthly-recap__label">다이어리</span>
        </div>
        <div className="monthly-recap__stat">
          <BookOpen size={13} className="monthly-recap__icon monthly-recap__icon--scrap" />
          <span className="monthly-recap__value">
            <strong>{stats.scrapCount}</strong>
            <span className="monthly-recap__unit">개</span>
          </span>
          <span className="monthly-recap__label">스크랩</span>
        </div>
        {stats.topTags.length > 0 && (
          <div className="monthly-recap__tags">
            <span className="monthly-recap__tags-label">자주</span>
            {stats.topTags.map((t) => (
              <span key={t} className="monthly-recap__tag">{t}</span>
            ))}
          </div>
        )}
      </div>
      {oneLine && <span className="monthly-recap__line">"{oneLine}"</span>}
    </div>
  )
}
