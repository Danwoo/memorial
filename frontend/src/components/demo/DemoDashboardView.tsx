import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  MessageSquare, BookOpen, PenLine, Network,
  Flame, TrendingUp, Zap, Calendar,
} from 'lucide-react'
import {
  DEMO_BRIEFING, DEMO_STREAK, DEMO_STATS, DEMO_ACTIVITY, DEMO_INSIGHTS,
} from '../../data/demo-data'
import '../DashboardView.css'

type Tab = 'briefing' | 'weekly' | 'monthly'

export default function DemoDashboardView() {
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<Tab>('briefing')
  const briefing = DEMO_BRIEFING
  const streak = DEMO_STREAK
  const stats = DEMO_STATS
  const activity = DEMO_ACTIVITY
  const insights = DEMO_INSIGHTS

  const maxCount = Math.max(...activity.map(d => d.count), 1)

  const quickActions = [
    { icon: <PenLine size={20} />, label: '저널 쓰기', desc: '오늘을 기록하세요', path: '/demo/journal' },
    { icon: <BookOpen size={20} />, label: '기억 추가', desc: '새로운 지식을 저장', path: '/demo/memories' },
    { icon: <MessageSquare size={20} />, label: 'AI 대화', desc: 'Socrates에게 질문', path: '/demo/chat' },
    { icon: <Network size={20} />, label: '그래프 탐색', desc: '연결 발견하기', path: '/demo/graph' },
  ]

  return (
    <div className="dashboard-view">
      <div className="dashboard-tabs">
        {(['briefing', 'weekly', 'monthly'] as Tab[]).map(tab => (
          <button
            key={tab}
            className={`dashboard-tab ${activeTab === tab ? 'active' : ''}`}
            onClick={() => setActiveTab(tab)}
          >
            {tab === 'briefing' ? '오늘의 브리핑' : tab === 'weekly' ? '주간 리포트' : '월간 리포트'}
          </button>
        ))}
      </div>

      {activeTab !== 'briefing' ? (
        <div className="report-hero">
          <div className="report-hero-card">
            <h2>{activeTab === 'weekly' ? '주간' : '월간'} AI 리포트</h2>
            <p className="report-summary">
              {activeTab === 'weekly'
                ? '이번 주에는 AI 기술과 인문학의 교차점에 대한 탐구가 두드러졌습니다. 특히 트랜스포머 아키텍처와 스토아 철학의 연결을 발견한 것이 인상적입니다.'
                : '이번 달에는 42개의 메모리를 저장하고 5개의 저널을 작성했습니다. AI, 심리학, 철학 분야에서 꾸준한 학습이 이루어졌습니다.'}
            </p>
            <div className="report-stats-row">
              <div className="report-stat"><strong>{activeTab === 'weekly' ? 5 : 18}</strong><span>메모리</span></div>
              <div className="report-stat"><strong>{activeTab === 'weekly' ? 2 : 5}</strong><span>저널</span></div>
            </div>
          </div>
        </div>
      ) : (
        <>
          {/* 히어로 인사 */}
          <div className="dashboard-hero">
            <div className="hero-card">
              <h1 className="hero-greeting">안녕하세요! 👋</h1>
              <div className="hero-stats">
                <span className="hero-badge"><Flame size={14} /> {briefing.streak.current}일 연속</span>
                <span className="hero-badge"><BookOpen size={14} /> 오늘 {briefing.today_memories.count}개</span>
                {briefing.unreviewed_count > 0 && (
                  <span className="hero-badge hero-badge--accent"><Zap size={14} /> 미확인 {briefing.unreviewed_count}개</span>
                )}
              </div>
              {briefing.suggested_question && (
                <div className="hero-question">
                  <span className="hero-question-label">오늘의 질문</span>
                  <p
                    className="hero-question-text"
                    onClick={() => navigate('/demo/chat', { state: { initialMessage: briefing.suggested_question } })}
                    role="button"
                    tabIndex={0}
                  >
                    "{briefing.suggested_question}"
                  </p>
                </div>
              )}
            </div>
          </div>

          {/* 퀵 액션 */}
          <section className="dashboard-section">
            <div className="quick-actions-grid">
              {quickActions.map(a => (
                <button key={a.label} className="quick-action-card" onClick={() => navigate(a.path)}>
                  <span className="quick-action-icon">{a.icon}</span>
                  <strong>{a.label}</strong>
                  <span className="quick-action-desc">{a.desc}</span>
                </button>
              ))}
            </div>
          </section>

          {/* 스트릭 */}
          <section className="dashboard-section">
            <h2 className="section-title"><Flame size={18} /> 연속 기록</h2>
            <div className="streak-card">
              <div className="streak-main">
                <span className="streak-number">{streak.current_streak}</span>
                <span className="streak-label">일 연속</span>
              </div>
              <div className="streak-details">
                <div><strong>{streak.longest_streak}</strong> 최장 기록</div>
                <div><strong>{streak.total_active_days}</strong> 총 활동일</div>
              </div>
            </div>
          </section>

          {/* 활동 히트맵 */}
          <section className="dashboard-section">
            <h2 className="section-title"><Calendar size={18} /> 활동 히트맵</h2>
            <div className="heatmap-container">
              <div className="heatmap-grid">
                {activity.map(d => (
                  <div
                    key={d.date}
                    className="heatmap-cell"
                    style={{ opacity: d.count === 0 ? 0.1 : 0.2 + (d.count / maxCount) * 0.8 }}
                    title={`${d.date}: ${d.count}개`}
                  />
                ))}
              </div>
            </div>
          </section>

          {/* 태그 */}
          <section className="dashboard-section">
            <h2 className="section-title"><TrendingUp size={18} /> 주요 태그</h2>
            <div className="tags-list">
              {stats.top_tags.map(t => (
                <div key={t.tag} className="tag-row">
                  <span className="tag-name">{t.tag}</span>
                  <div className="tag-bar-container">
                    <div
                      className="tag-bar"
                      style={{ width: `${(t.count / (stats.top_tags[0]?.count || 1)) * 100}%` }}
                    />
                  </div>
                  <span className="tag-count">{t.count}</span>
                </div>
              ))}
            </div>
          </section>

          {/* AI 인사이트 */}
          <section className="dashboard-section">
            <h2 className="section-title"><Zap size={18} /> AI 인사이트</h2>
            <div className="insights-grid">
              {insights.map((ins, i) => (
                <div key={i} className="insight-card" onClick={() => navigate(ins.cta_path)} role="button" tabIndex={0}>
                  <span className="insight-icon">{ins.icon}</span>
                  <strong className="insight-title">{ins.title}</strong>
                  <p className="insight-desc">{ins.description}</p>
                  <span className="insight-cta">{ins.cta_label} →</span>
                </div>
              ))}
            </div>
          </section>
        </>
      )}
    </div>
  )
}
