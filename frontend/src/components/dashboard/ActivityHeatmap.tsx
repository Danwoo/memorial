import { useState, useMemo, useCallback } from 'react'
import { TrendingUp } from 'lucide-react'
import type { ActivityData } from '../../types'

function getHeatStyle(count: number, max: number): React.CSSProperties {
  if (count === 0) return { backgroundColor: 'var(--bg-tertiary)' }
  const intensity = Math.min(count / Math.max(max, 1), 1)
  const opacity = 0.25 + intensity * 0.75
  return { backgroundColor: 'var(--accent-primary)', opacity }
}

const WEEKDAY_LABELS = ['월', '화', '수', '목', '금', '토', '일']

function buildCalendarGrid(activity: ActivityData[]) {
  if (activity.length === 0) return { weeks: [] as (ActivityData | null)[][], monthLabels: [] as { label: string; col: number }[] }

  const dateMap = new Map(activity.map(a => [a.date, a]))
  const endDate = new Date()
  const startDate = new Date(endDate)
  startDate.setDate(startDate.getDate() - (activity.length - 1))

  // 첫 주 월요일로 정렬
  const firstDay = startDate.getDay()
  const mondayOffset = firstDay === 0 ? 6 : firstDay - 1
  startDate.setDate(startDate.getDate() - mondayOffset)

  const weeks: (ActivityData | null)[][] = []
  const monthLabels: { label: string; col: number }[] = []
  let currentWeek: (ActivityData | null)[] = []
  let lastMonth = -1
  const cursor = new Date(startDate)

  while (cursor <= endDate || currentWeek.length > 0) {
    const dateStr = cursor.toISOString().slice(0, 10)
    const dayOfWeek = cursor.getDay()
    const mondayIdx = dayOfWeek === 0 ? 6 : dayOfWeek - 1

    if (mondayIdx === 0 && currentWeek.length > 0) {
      weeks.push(currentWeek)
      currentWeek = []
    }

    const month = cursor.getMonth()
    if (month !== lastMonth && mondayIdx === 0) {
      const monthNames = ['1월', '2월', '3월', '4월', '5월', '6월', '7월', '8월', '9월', '10월', '11월', '12월']
      monthLabels.push({ label: monthNames[month], col: weeks.length })
      lastMonth = month
    }

    if (cursor <= endDate) {
      currentWeek.push(dateMap.get(dateStr) || { date: dateStr, count: 0 })
    }

    cursor.setDate(cursor.getDate() + 1)
    if (cursor > endDate && currentWeek.length > 0) {
      weeks.push(currentWeek)
      break
    }
  }

  return { weeks, monthLabels }
}

interface ActivityHeatmapProps {
  activity: ActivityData[]
}

export default function ActivityHeatmap({ activity }: ActivityHeatmapProps) {
  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null)

  const maxActivity = useMemo(
    () => Math.max(...activity.map(a => a.count), 1),
    [activity],
  )

  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), [])

  const calendarData = useMemo(() => buildCalendarGrid(activity), [activity])

  const handleCellHover = useCallback((e: React.MouseEvent, day: ActivityData) => {
    const rect = e.currentTarget.getBoundingClientRect()
    setTooltip({
      text: `${day.date} · ${day.count}개 활동`,
      x: rect.left + rect.width / 2,
      y: rect.top - 8,
    })
  }, [])

  if (activity.length === 0) return null

  return (
    <div className="activity-section">
      <h2>
        <TrendingUp size={18} />
        최근 활동
      </h2>
      <div className="calendar-heatmap" onMouseLeave={() => setTooltip(null)}>
        {/* 월 라벨 */}
        <div className="calendar-month-labels">
          <div className="calendar-weekday-spacer" />
          {calendarData.monthLabels.map((ml, i) => (
            <span
              key={i}
              className="calendar-month-label"
              style={{ gridColumnStart: ml.col + 2 }}
            >
              {ml.label}
            </span>
          ))}
        </div>
        <div className="calendar-grid-wrapper">
          {/* 요일 라벨 */}
          <div className="calendar-weekday-labels">
            {WEEKDAY_LABELS.map((label, i) => (
              <span key={i} className="calendar-weekday-label">{i % 2 === 0 ? label : ''}</span>
            ))}
          </div>
          {/* 히트맵 셀 그리드 */}
          <div className="calendar-cells" style={{ gridTemplateColumns: `repeat(${calendarData.weeks.length}, 14px)` }}>
            {calendarData.weeks.map((week, wi) =>
              week.map((day, di) =>
                day ? (
                  <div
                    key={`${wi}-${di}`}
                    className={`heatmap-cell${day.date === todayStr ? ' heatmap-cell--today' : ''}`}
                    style={{ ...getHeatStyle(day.count, maxActivity), gridColumn: wi + 1, gridRow: di + 1 }}
                    onMouseEnter={(e) => handleCellHover(e, day)}
                    onMouseLeave={() => setTooltip(null)}
                  />
                ) : null
              )
            )}
          </div>
        </div>
      </div>
      {tooltip && (
        <div
          className="heatmap-tooltip"
          style={{ left: tooltip.x, top: tooltip.y }}
        >
          {tooltip.text}
        </div>
      )}
      <div className="heatmap-legend">
        <span>적음</span>
        <div className="heatmap-legend-cells">
          {[0, 0.25, 0.5, 0.75, 1].map((v, i) => (
            <div
              key={i}
              className="heatmap-cell"
              style={v === 0
                ? { backgroundColor: 'var(--bg-tertiary)' }
                : { backgroundColor: 'var(--accent-primary)', opacity: 0.25 + v * 0.75 }}
            />
          ))}
        </div>
        <span>많음</span>
      </div>
    </div>
  )
}
