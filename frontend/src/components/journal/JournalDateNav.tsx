import { ChevronLeft, ChevronRight, Calendar } from 'lucide-react'

// YYYY-MM-DD 형식 날짜 헬퍼
function formatDateKo(dateStr: string): string {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('ko-KR', { year: 'numeric', month: 'long', day: 'numeric' })
}

function shiftDate(dateStr: string, days: number): string {
  const d = new Date(dateStr + 'T00:00:00')
  d.setDate(d.getDate() + days)
  return d.toISOString().slice(0, 10)
}

interface JournalDateNavProps {
  currentDate: string
  todayStr: string
  isToday: boolean
  onDateChange: (date: string) => void
  onToggleDatePicker: () => void
}

export function JournalDateNav({
  currentDate,
  todayStr,
  isToday,
  onDateChange,
  onToggleDatePicker,
}: JournalDateNavProps) {
  return (
    <div className="diary-date-nav">
      <button
        className="diary-date-nav__btn"
        onClick={() => onDateChange(shiftDate(currentDate, -1))}
        type="button"
        aria-label="이전 날짜"
      >
        <ChevronLeft size={18} />
      </button>
      <button
        className="diary-date-nav__current"
        onClick={onToggleDatePicker}
        type="button"
      >
        <Calendar size={14} />
        <span>{isToday ? '오늘의 다이어리' : formatDateKo(currentDate)}</span>
      </button>
      <button
        className="diary-date-nav__btn"
        onClick={() => onDateChange(shiftDate(currentDate, 1))}
        disabled={currentDate >= todayStr}
        type="button"
        aria-label="다음 날짜"
      >
        <ChevronRight size={18} />
      </button>
      {!isToday && (
        <button
          className="diary-date-nav__today"
          onClick={() => onDateChange(todayStr)}
          type="button"
        >
          오늘
        </button>
      )}
    </div>
  )
}
