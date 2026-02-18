import { useEffect, useState, useMemo, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Flame, Trophy, Calendar, TrendingUp, Tag,
  BookOpen, Lightbulb, MessageSquare, Network,
  Pencil, Link2, Sparkles,
} from 'lucide-react'
import type { StreakData, StatsData, ActivityData, BriefingData, DailyInsight } from '../types'
import { fetchStreak, fetchStats, fetchActivity, fetchBriefing, fetchDailyInsights } from '../api'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import './DashboardView.css'

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 6) return '새벽이에요'
  if (hour < 12) return '좋은 아침이에요'
  if (hour < 18) return '좋은 오후예요'
  return '좋은 저녁이에요'
}

function getStreakMessage(streak: number): string {
  if (streak === 0) return '오늘 기록을 시작해보세요!'
  if (streak === 1) return '첫 걸음을 내딛었어요!'
  if (streak < 3) return '좋은 시작이에요!'
  if (streak < 7) return '습관이 만들어지고 있어요!'
  if (streak < 14) return '꾸준함이 빛나고 있어요!'
  if (streak < 30) return '대단해요! 2주 이상 연속!'
  return '한 달 넘는 연속 기록!'
}

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

export default function DashboardView() {
  const navigate = useNavigate()
  const { user } = useAuth()
  const toast = useToast()

  const [briefing, setBriefing] = useState<BriefingData | null>(null)
  const [streak, setStreak] = useState<StreakData | null>(null)
  const [stats, setStats] = useState<StatsData | null>(null)
  const [activity, setActivity] = useState<ActivityData[]>([])
  const [dailyInsights, setDailyInsights] = useState<DailyInsight[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [briefingData, streakData, statsData, activityData, insightsData] = await Promise.all([
          fetchBriefing().catch(() => null),
          fetchStreak(),
          fetchStats(),
          fetchActivity(60),
          fetchDailyInsights().catch(() => ({ insights: [] })),
        ])
        setBriefing(briefingData)
        setStreak(streakData)
        setStats(statsData)
        setActivity(activityData.activity)
        setDailyInsights(insightsData.insights)
      } catch (err) {
        console.error('대시보드 데이터 로딩 실패:', err)
        toast.error('대시보드 데이터를 불러오지 못했습니다')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [toast])

  const maxActivity = useMemo(
    () => Math.max(...activity.map(a => a.count), 1),
    [activity],
  )

  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), [])

  const calendarData = useMemo(() => buildCalendarGrid(activity), [activity])

  const [tooltip, setTooltip] = useState<{ text: string; x: number; y: number } | null>(null)

  const handleCellHover = useCallback((e: React.MouseEvent, day: ActivityData) => {
    const rect = e.currentTarget.getBoundingClientRect()
    setTooltip({
      text: `${day.date} · ${day.count}개 활동`,
      x: rect.left + rect.width / 2,
      y: rect.top - 8,
    })
  }, [])

  const displayName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || ''

  if (loading) {
    return (
      <div className="dashboard-view">
        <div className="skeleton skeleton-title" style={{ width: '60%' }} />
        <div className="skeleton skeleton-card" style={{ height: 160 }} />
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: 12, marginBottom: 20 }}>
          <div className="skeleton skeleton-card" style={{ height: 100 }} />
          <div className="skeleton skeleton-card" style={{ height: 100 }} />
          <div className="skeleton skeleton-card" style={{ height: 100 }} />
          <div className="skeleton skeleton-card" style={{ height: 100 }} />
        </div>
        <div className="skeleton skeleton-card" style={{ height: 120 }} />
      </div>
    )
  }

  return (
    <div className="dashboard-view">
      {/* 히어로 브리핑 카드 */}
      <div className="dashboard-hero">
        <div className="hero-greeting">
          <h1>{getGreeting()}{displayName ? `, ${displayName}님` : ''}</h1>
          <div className="hero-stats">
            {stats && (
              <>
                <span className="hero-stat-item">
                  <BookOpen size={14} />
                  오늘 기억 {briefing?.today_memories.count ?? 0}개
                </span>
                {briefing && briefing.unreviewed_count > 0 && (
                  <span className="hero-stat-item hero-stat-action">
                    <Pencil size={14} />
                    미회고 {briefing.unreviewed_count}개
                  </span>
                )}
                {streak && streak.current_streak > 0 && (
                  <span className="hero-stat-item">
                    <Flame size={14} />
                    {streak.current_streak}일 연속
                  </span>
                )}
              </>
            )}
          </div>
        </div>
        {briefing?.suggested_question && (
          <button
            className="hero-question"
            onClick={() => navigate('/journal', { state: { prefillQuestion: briefing.suggested_question } })}
          >
            <Lightbulb size={18} className="hero-question-icon" />
            <div className="hero-question-body">
              <span className="hero-question-label">오늘의 질문</span>
              <span className="hero-question-text">{briefing.suggested_question}</span>
            </div>
          </button>
        )}
      </div>

      {/* 퀵 액션 그리드 */}
      <div className="quick-actions-grid">
        <button className="quick-action-card" onClick={() => navigate('/journal')}>
          <div className="quick-action-icon" style={{ background: 'rgba(99, 102, 241, 0.1)', color: '#6366f1' }}>
            <Pencil size={22} />
          </div>
          <div className="quick-action-body">
            <span className="quick-action-title">저널 쓰기</span>
            <span className="quick-action-sub">
              {briefing && briefing.unreviewed_count > 0
                ? `미회고 ${briefing.unreviewed_count}개`
                : '오늘의 생각 기록'}
            </span>
          </div>
        </button>

        <button className="quick-action-card" onClick={() => navigate('/memories')}>
          <div className="quick-action-icon" style={{ background: 'rgba(52, 211, 153, 0.1)', color: '#34d399' }}>
            <BookOpen size={22} />
          </div>
          <div className="quick-action-body">
            <span className="quick-action-title">기억 탐색</span>
            <span className="quick-action-sub">
              {stats ? `총 ${stats.overview.total_memories}개` : '기억 둘러보기'}
            </span>
          </div>
        </button>

        <button className="quick-action-card" onClick={() => navigate('/chat')}>
          <div className="quick-action-icon" style={{ background: 'rgba(251, 146, 60, 0.1)', color: '#fb923c' }}>
            <MessageSquare size={22} />
          </div>
          <div className="quick-action-body">
            <span className="quick-action-title">Socrates 대화</span>
            <span className="quick-action-sub">AI와 함께 성찰</span>
          </div>
        </button>

        <button className="quick-action-card" onClick={() => navigate('/graph')}>
          <div className="quick-action-icon" style={{ background: 'rgba(96, 165, 250, 0.1)', color: '#60a5fa' }}>
            <Network size={22} />
          </div>
          <div className="quick-action-body">
            <span className="quick-action-title">지식 그래프</span>
            <span className="quick-action-sub">연결 시각화</span>
          </div>
        </button>
      </div>

      {/* AI 인사이트 */}
      {dailyInsights.length > 0 && (
        <div className="ai-insights-section">
          <h2>
            <Sparkles size={18} />
            AI가 발견한 것
          </h2>
          <div className="insight-cards">
            {dailyInsights.map((insight, i) => {
              const IconMap: Record<string, React.ReactNode> = {
                TrendingUp: <TrendingUp size={18} />,
                Link2: <Link2 size={18} />,
                Pencil: <Pencil size={18} />,
              }
              return (
                <button
                  key={i}
                  className="insight-card"
                  onClick={() => navigate(insight.cta_path)}
                >
                  <span className="insight-card-icon">
                    {IconMap[insight.icon] || <Lightbulb size={18} />}
                  </span>
                  <div className="insight-card-body">
                    <div className="insight-card-title">{insight.title}</div>
                    <div className="insight-card-desc">{insight.description}</div>
                    <div className="insight-card-cta">{insight.cta_label} →</div>
                  </div>
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* 스트릭 카드 */}
      {streak && (
        <div className="streak-card">
          <div className="streak-main">
            <Flame size={32} className="streak-icon" />
            <div className="streak-number">{streak.current_streak}</div>
            <div className="streak-unit">일 연속</div>
          </div>
          <p className="streak-message">{getStreakMessage(streak.current_streak)}</p>
          <div className="streak-stats">
            <div className="streak-stat">
              <Trophy size={16} />
              <span>최장 {streak.longest_streak}일</span>
            </div>
            <div className="streak-stat">
              <Calendar size={16} />
              <span>총 {streak.total_active_days}일 활동</span>
            </div>
          </div>
        </div>
      )}

      {/* 활동 히트맵 (캘린더 레이아웃) */}
      {activity.length > 0 && (
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
      )}

      {/* 인기 태그 */}
      {stats && stats.top_tags.length > 0 && (
        <div className="tags-section">
          <h2>
            <Tag size={18} />
            주요 주제
          </h2>
          <div className="tag-list">
            {stats.top_tags.map(t => (
              <div key={t.tag} className="tag-item">
                <span className="tag-name">#{t.tag}</span>
                <span className="tag-count">{t.count}</span>
                <div className="tag-bar">
                  <div
                    className="tag-bar-fill"
                    style={{ width: `${(t.count / stats.top_tags[0].count) * 100}%` }}
                  />
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
