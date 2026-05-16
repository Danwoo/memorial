import { useMemo } from 'react'
import { ChevronLeft, ChevronRight, Sparkles } from 'lucide-react'
import type { ActivityData } from '../../types'
import type { DiaryDateInfo } from '../../types/diary'
import './MonthlyCalendar.css'

const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토']

interface MonthlyCalendarProps {
  year: number
  month: number
  journalDates: DiaryDateInfo[]
  activityData: ActivityData[]
  onDateClick: (dateStr: string) => void
  onMonthChange: (year: number, month: number) => void
  selectedDate?: string | null
  streakBadge?: React.ReactNode
  weekSummary?: React.ReactNode
  /** 망각 곡선 — 다시 만나볼 만한 날짜들 (3d / 1w / 1m / 3m / 1y 전) */
  recallDates?: Set<string>
}

/** 해당 월의 달력 데이터 생성 */
function buildMonthGrid(year: number, month: number) {
  const firstDay = new Date(year, month, 1)
  const lastDay = new Date(year, month + 1, 0)
  const startDayOfWeek = firstDay.getDay() // 0=일 ~ 6=토

  const totalDays = lastDay.getDate()
  const cells: (number | null)[] = []

  // 이전 달 빈 칸
  for (let i = 0; i < startDayOfWeek; i++) {
    cells.push(null)
  }
  // 이번 달 날짜
  for (let d = 1; d <= totalDays; d++) {
    cells.push(d)
  }

  return cells
}

/** YYYY-MM-DD 형식으로 변환 */
function toDateStr(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}


/** 무드 → 다이어리 칩 배경색 */
function getMoodBg(mood: string | null | undefined): string {
  switch (mood) {
    case 'POSITIVE': return 'rgba(34,197,94,0.18)'
    case 'NEGATIVE': return 'rgba(239,68,68,0.18)'
    case 'MIXED':    return 'rgba(234,179,8,0.18)'
    default:         return 'var(--accent-bg)'
  }
}

const MONTH_NAMES = [
  '1월', '2월', '3월', '4월', '5월', '6월',
  '7월', '8월', '9월', '10월', '11월', '12월',
]

export default function MonthlyCalendar({
  year, month, journalDates, activityData, onDateClick, onMonthChange,
  selectedDate, streakBadge, weekSummary, recallDates,
}: MonthlyCalendarProps) {
  const cells = useMemo(() => buildMonthGrid(year, month), [year, month])
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), [])

  // 저널 날짜 맵 (date → DiaryDateInfo)
  const journalMap = useMemo(() => {
    const map = new Map<string, DiaryDateInfo>()
    for (const d of journalDates) {
      map.set(d.date, d)
    }
    return map
  }, [journalDates])

  // 활동 데이터 맵 (date → ActivityData)
  const activityMap = useMemo(() => {
    const map = new Map<string, ActivityData>()
    for (const a of activityData) {
      map.set(a.date, a)
    }
    return map
  }, [activityData])

  // 이달 최대 활동 점수 (정규화 기준)
  const monthlyMax = useMemo(() => {
    let max = 0
    for (const day of cells) {
      if (day === null) continue
      const dateStr = toDateStr(year, month, day)
      const score = (activityMap.get(dateStr)?.count ?? 0) + (journalMap.has(dateStr) ? 1 : 0)
      if (score > max) max = score
    }
    return Math.max(max, 1)
  }, [cells, activityMap, journalMap, year, month])

  const handlePrev = () => {
    if (month === 0) onMonthChange(year - 1, 11)
    else onMonthChange(year, month - 1)
  }

  const handleNext = () => {
    if (month === 11) onMonthChange(year + 1, 0)
    else onMonthChange(year, month + 1)
  }

  return (
    <div className="monthly-calendar">
      {/* 월 네비게이션 */}
      <div className="monthly-calendar__nav">
        <button
          className="monthly-calendar__arrow"
          onClick={handlePrev}
          aria-label="이전 달"
          type="button"
        >
          <ChevronLeft size={20} />
        </button>
        <div className="monthly-calendar__title-area">
          <h2 className="monthly-calendar__title">
            {year}년 {MONTH_NAMES[month]}
          </h2>
          {streakBadge}
          {weekSummary}
        </div>
        <button
          className="monthly-calendar__arrow"
          onClick={handleNext}
          aria-label="다음 달"
          type="button"
        >
          <ChevronRight size={20} />
        </button>
      </div>

      {/* 요일 헤더 */}
      <div className="monthly-calendar__weekdays">
        {WEEKDAY_LABELS.map((label, i) => (
          <div
            key={label}
            className={`monthly-calendar__weekday${i === 0 ? ' monthly-calendar__weekday--sun' : i === 6 ? ' monthly-calendar__weekday--sat' : ''}`}
          >
            {label}
          </div>
        ))}
      </div>

      {/* 날짜 그리드 */}
      <div className="monthly-calendar__grid">
        {cells.map((day, i) => {
          if (day === null) {
            return <div key={`empty-${i}`} className="monthly-calendar__cell monthly-calendar__cell--empty" />
          }

          const dateStr = toDateStr(year, month, day)
          const isToday = dateStr === todayStr
          const isSelected = dateStr === selectedDate
          const journal = journalMap.get(dateStr)
          const activity = activityMap.get(dateStr)

          const score = (activity?.count ?? 0) + (journal ? 1 : 0)
          const actLevel = score === 0 ? 0 : (Math.ceil((score / monthlyMax) * 4) as 1 | 2 | 3 | 4)

          // AI 인사이트 별: 활동이 풍부한 날 (다이어리 + 스크랩 2개 이상)
          const hasInsight = score >= 3
          // 망각 곡선: 3일/1주/1개월/3개월/1년 전 — 다시 만나볼 시간
          const hasRecall = recallDates?.has(dateStr) ?? false

          return (
            <button
              key={dateStr}
              className={`monthly-calendar__cell${isToday ? ' monthly-calendar__cell--today' : ''}${actLevel > 0 ? ' monthly-calendar__cell--has-journal' : ''}${isSelected ? ' monthly-calendar__cell--selected' : ''}`}
              data-activity={actLevel > 0 ? actLevel : undefined}
              onClick={() => onDateClick(dateStr)}
              type="button"
            >
              <div className="monthly-calendar__cell-top">
                <div className="monthly-calendar__cell-top-left">
                  {hasRecall && (
                    <span
                      className="monthly-calendar__recall-dot"
                      aria-hidden="true"
                      title="다시 만나볼 시간이에요"
                    />
                  )}
                  <span className="monthly-calendar__day">{day}</span>
                </div>
                {hasInsight && (
                  <span
                    className="monthly-calendar__insight-star"
                    aria-hidden="true"
                    title="이 날의 인사이트"
                  >
                    <Sparkles size={11} strokeWidth={2} />
                  </span>
                )}
              </div>
              <div className="monthly-calendar__chips">
                {journal?.tags?.slice(0, 2).map(tag => (
                  <span
                    key={tag}
                    className="monthly-calendar__diary-chip"
                    style={{ backgroundColor: getMoodBg(journal.mood) }}
                  >
                    {tag}
                  </span>
                ))}
                <div className="monthly-calendar__tag-chips">
                  {activity?.tags?.slice(0, 2).map(tag => (
                    <span key={tag} className="monthly-calendar__tag-chip">
                      {tag}
                    </span>
                  ))}
                </div>
              </div>
            </button>
          )
        })}
      </div>

    </div>
  )
}
