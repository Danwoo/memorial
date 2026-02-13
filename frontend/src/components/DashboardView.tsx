import { useEffect, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  Flame, Trophy, Calendar, TrendingUp, Tag,
  BookOpen, Lightbulb, Link2, Pencil,
} from 'lucide-react'
import type { StreakData, StatsData, ActivityData, BriefingData } from '../types'
import { fetchStreak, fetchStats, fetchActivity, fetchBriefing } from '../api'
import { useToast } from '../contexts/ToastContext'
import './DashboardView.css'

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

export default function DashboardView() {
  const navigate = useNavigate()
  const toast = useToast()

  const [briefing, setBriefing] = useState<BriefingData | null>(null)
  const [streak, setStreak] = useState<StreakData | null>(null)
  const [stats, setStats] = useState<StatsData | null>(null)
  const [activity, setActivity] = useState<ActivityData[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const load = async () => {
      setLoading(true)
      try {
        const [briefingData, streakData, statsData, activityData] = await Promise.all([
          fetchBriefing().catch(() => null),
          fetchStreak(),
          fetchStats(),
          fetchActivity(60),
        ])
        setBriefing(briefingData)
        setStreak(streakData)
        setStats(statsData)
        setActivity(activityData.activity)
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

  if (loading) {
    return (
      <div className="dashboard-view">
        <div className="dashboard-loading">불러오는 중...</div>
      </div>
    )
  }

  return (
    <div className="dashboard-view">
      <h1 className="dashboard-title">대시보드</h1>

      {/* 오늘의 브리핑 */}
      {briefing && (
        <div className="briefing-section">
          <h2 className="briefing-heading">오늘의 브리핑</h2>
          <div className="briefing-grid">
            <button
              className="briefing-card"
              onClick={() => navigate('/memories')}
            >
              <div className="briefing-card-icon">
                <BookOpen size={20} />
              </div>
              <div className="briefing-card-body">
                <div className="briefing-card-value">
                  {briefing.today_memories.count > 0
                    ? `오늘 ${briefing.today_memories.count}개의 새 기억`
                    : '아직 오늘의 기억이 없어요'}
                </div>
                {briefing.today_memories.topics.length > 0 && (
                  <div className="briefing-card-tags">
                    {briefing.today_memories.topics.map(t => (
                      <span key={t} className="briefing-tag">#{t}</span>
                    ))}
                  </div>
                )}
                {briefing.today_memories.count === 0 && (
                  <div className="briefing-card-hint">첫 메모리를 추가해보세요!</div>
                )}
              </div>
            </button>

            <button
              className="briefing-card"
              onClick={() => navigate('/journal')}
            >
              <div className="briefing-card-icon">
                <Pencil size={20} />
              </div>
              <div className="briefing-card-body">
                <div className="briefing-card-value">
                  {briefing.unreviewed_count > 0
                    ? `회고하지 않은 기억 ${briefing.unreviewed_count}개`
                    : '모든 기억을 회고했어요!'}
                </div>
                {briefing.unreviewed_count > 0 && (
                  <div className="briefing-card-cta">저널 쓰러 가기 →</div>
                )}
              </div>
            </button>

            <button
              className="briefing-card briefing-card-wide"
              onClick={() => navigate('/journal', { state: { prefillQuestion: briefing.suggested_question } })}
            >
              <div className="briefing-card-icon">
                <Lightbulb size={20} />
              </div>
              <div className="briefing-card-body">
                <div className="briefing-card-label">오늘의 질문</div>
                <div className="briefing-card-question">{briefing.suggested_question}</div>
              </div>
            </button>

            {briefing.connection_hint && (
              <button className="briefing-card briefing-card-wide">
                <div className="briefing-card-icon">
                  <Link2 size={20} />
                </div>
                <div className="briefing-card-body">
                  <div className="briefing-card-label">연결 발견</div>
                  <div className="briefing-card-value">{briefing.connection_hint}</div>
                </div>
              </button>
            )}
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

      {/* 통계 카드 */}
      {stats && (
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-value">{stats.overview.total_memories}</div>
            <div className="stat-label">전체 메모리</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.overview.total_this_week}</div>
            <div className="stat-label">이번 주</div>
          </div>
          <div className="stat-card">
            <div className="stat-value">{stats.overview.total_this_month}</div>
            <div className="stat-label">이번 달</div>
          </div>
        </div>
      )}

      {/* 활동 히트맵 */}
      {activity.length > 0 && (
        <div className="activity-section">
          <h2>
            <TrendingUp size={18} />
            최근 활동
          </h2>
          <div className="activity-heatmap">
            {activity.map(day => (
              <div
                key={day.date}
                className="heatmap-cell"
                style={getHeatStyle(day.count, maxActivity)}
                title={`${day.date}: ${day.count}개`}
              />
            ))}
          </div>
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
