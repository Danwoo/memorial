import { useNavigate } from 'react-router-dom'
import {
  Flame, Tag, BookOpen, Lightbulb, MessageSquare,
  Network, Pencil, Link2, Sparkles, TrendingUp,
} from 'lucide-react'
import type { StreakData, StatsData, ActivityData, BriefingData, DailyInsight } from '../../types'
import StreakCard from './StreakCard'
import ActivityHeatmap from './ActivityHeatmap'

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 6) return '새벽이에요'
  if (hour < 12) return '좋은 아침이에요'
  if (hour < 18) return '좋은 오후예요'
  return '좋은 저녁이에요'
}

interface BriefingTabProps {
  displayName: string
  briefing: BriefingData | null
  streak: StreakData | null
  stats: StatsData | null
  activity: ActivityData[]
  dailyInsights: DailyInsight[]
}

export default function BriefingTab({ displayName, briefing, streak, stats, activity, dailyInsights }: BriefingTabProps) {
  const navigate = useNavigate()

  return (
    <>
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
      {streak && <StreakCard streak={streak} />}

      {/* 활동 히트맵 */}
      <ActivityHeatmap activity={activity} />

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
    </>
  )
}
