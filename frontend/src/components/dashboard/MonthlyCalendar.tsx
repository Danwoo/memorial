import { useMemo } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import type { ActivityData } from '../../types'
import type { JournalDateInfo } from '../../types/journal'
import './MonthlyCalendar.css'

const WEEKDAY_LABELS = ['일', '월', '화', '수', '목', '금', '토']

interface MonthlyCalendarProps {
  year: number
  month: number
  journalDates: JournalDateInfo[]
  activityData: ActivityData[]
  onDateClick: (dateStr: string) => void
  onMonthChange: (year: number, month: number) => void
  selectedDate?: string | null
  streakBadge?: React.ReactNode
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

/** 무드 → 도트 색상 */
function getMoodColor(mood: string | null): string {
  switch (mood) {
    case 'POSITIVE': return 'var(--color-success)'
    case 'NEGATIVE': return 'var(--color-error)'
    case 'MIXED': return 'var(--color-warning)'
    default: return 'var(--accent-primary)'
  }
}

const MONTH_NAMES = [
  '1월', '2월', '3월', '4월', '5월', '6월',
  '7월', '8월', '9월', '10월', '11월', '12월',
]

export default function MonthlyCalendar({
  year, month, journalDates, activityData, onDateClick, onMonthChange,
  selectedDate, streakBadge,
}: MonthlyCalendarProps) {
  const cells = useMemo(() => buildMonthGrid(year, month), [year, month])
  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), [])

  // 저널 날짜 맵 (date → JournalDateInfo)
  const journalMap = useMemo(() => {
    const map = new Map<string, JournalDateInfo>()
    for (const d of journalDates) {
      map.set(d.date, d)
    }
    return map
  }, [journalDates])

  // 활동 데이터 맵 (date → count)
  const activityMap = useMemo(() => {
    const map = new Map<string, number>()
    for (const a of activityData) {
      map.set(a.date, a.count)
    }
    return map
  }, [activityData])

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
          const activityCount = activityMap.get(dateStr) || 0

          return (
            <button
              key={dateStr}
              className={`monthly-calendar__cell${isToday ? ' monthly-calendar__cell--today' : ''}${journal ? ' monthly-calendar__cell--has-journal' : ''}${isSelected ? ' monthly-calendar__cell--selected' : ''}`}
              onClick={() => onDateClick(dateStr)}
              type="button"
            >
              <span className="monthly-calendar__day">{day}</span>
              <div className="monthly-calendar__indicators">
                {journal && (
                  <span
                    className="monthly-calendar__dot"
                    style={{ backgroundColor: getMoodColor(journal.mood) }}
                  />
                )}
                {activityCount > 0 && !journal && (
                  <span className="monthly-calendar__dot monthly-calendar__dot--activity" />
                )}
              </div>
              {activityCount > 0 && (
                <span className="monthly-calendar__badge">{activityCount}</span>
              )}
            </button>
          )
        })}
      </div>

      {/* 범례 */}
      <div className="monthly-calendar__legend">
        <span className="monthly-calendar__legend-item">
          <span className="monthly-calendar__dot" style={{ backgroundColor: 'var(--accent-primary)' }} />
          다이어리
        </span>
        <span className="monthly-calendar__legend-item">
          <span className="monthly-calendar__dot monthly-calendar__dot--activity" />
          활동
        </span>
      </div>
    </div>
  )
}
