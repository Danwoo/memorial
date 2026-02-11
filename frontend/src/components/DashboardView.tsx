import { useState, useEffect } from 'react'
import type { StatsData, DigestData } from '../types'
import { fetchStats, fetchDigest } from '../api'
import { getSourceIcon } from '../utils'
import './DashboardView.css'

export default function DashboardView() {
  const [stats, setStats] = useState<StatsData | null>(null)
  const [digest, setDigest] = useState<DigestData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    loadData()
  }, [])

  const loadData = async () => {
    try {
      setLoading(true)

      // 통계와 다이제스트를 병렬로 로드
      const [statsData, digestData] = await Promise.allSettled([
        fetchStats(),
        fetchDigest(),
      ])

      if (statsData.status === 'fulfilled') {
        setStats(statsData.value)
      } else {
        throw new Error('Failed to load stats')
      }

      if (digestData.status === 'fulfilled') {
        setDigest(digestData.value)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unknown error')
    } finally {
      setLoading(false)
    }
  }

  // 활동 차트의 최대값 산출 (막대 높이 비율 계산용)
  const getMaxActivity = () => {
    if (!stats) return 1
    return Math.max(...stats.recent_activity.map(a => a.count), 1)
  }

  if (loading) {
    return (
      <div className="dashboard-view">
        <div className="loading-state">
          <div className="loading-spinner"></div>
          <p>통계 로딩 중...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="dashboard-view">
        <div className="error-state">
          <div className="error-icon">⚠️</div>
          <h3>오류 발생</h3>
          <p>{error}</p>
          <button className="btn btn-primary" onClick={loadData}>다시 시도</button>
        </div>
      </div>
    )
  }

  if (!stats) return null

  return (
    <div className="dashboard-view">
      <div className="dashboard-header">
        <h1>📊 대시보드</h1>
        <p className="dashboard-subtitle">나의 지식 활동 요약</p>
      </div>

      {/* 오늘의 다이제스트 섹션 */}
      {digest && (digest.summary.memory_count > 0 || digest.insights.suggested_questions.length > 0) && (
        <div className="digest-section glass-card">
          <div className="digest-header">
            <h2>🌅 오늘의 현황</h2>
            <span className="digest-date">{digest.date}</span>
          </div>
          
          <div className="digest-stats">
            <div className="digest-stat">
              <span className="digest-stat-value">{digest.summary.memory_count}</span>
              <span className="digest-stat-label">새 메모리</span>
            </div>
            <div className="digest-stat">
              <span className="digest-stat-value">{digest.summary.journal_count}</span>
              <span className="digest-stat-label">일기</span>
            </div>
            <div className="digest-stat">
              <span className="digest-stat-value">{digest.insights.main_topics.length}</span>
              <span className="digest-stat-label">주제</span>
            </div>
          </div>

          {digest.insights.suggested_questions.length > 0 && (
            <div className="digest-questions">
              <h3>🤔 AI 추천 질문</h3>
              <ul>
                {digest.insights.suggested_questions.map((q, idx) => (
                  <li key={idx}>{q}</li>
                ))}
              </ul>
            </div>
          )}

          {digest.memories.length > 0 && (
            <div className="digest-memories">
              <h3>📝 오늘 저장한 내용</h3>
              <div className="digest-memory-list">
                {digest.memories.slice(0, 3).map((m, idx) => (
                  <div key={idx} className="digest-memory-item">
                    <span className="digest-memory-type">{m.type}</span>
                    <span className="digest-memory-title">{m.title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 통계 개요 카드 */}
      <div className="stats-grid">
        <div className="stat-card glass-card">
          <div className="stat-icon">📚</div>
          <div className="stat-content">
            <span className="stat-value">{stats.overview.total_memories}</span>
            <span className="stat-label">전체 메모리</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-icon">📅</div>
          <div className="stat-content">
            <span className="stat-value">{stats.overview.total_this_week}</span>
            <span className="stat-label">이번 주</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-icon">📆</div>
          <div className="stat-content">
            <span className="stat-value">{stats.overview.total_this_month}</span>
            <span className="stat-label">이번 달</span>
          </div>
        </div>

        <div className="stat-card glass-card">
          <div className="stat-icon">🔥</div>
          <div className="stat-content">
            <span className="stat-value">
              {stats.overview.most_active_day ? stats.overview.most_active_day.slice(5) : '-'}
            </span>
            <span className="stat-label">가장 활발한 날</span>
          </div>
        </div>
      </div>

      {/* 최근 활동 차트 */}
      <div className="chart-section glass-card">
        <h2>📈 최근 7일 활동</h2>
        <div className="activity-chart">
          {stats.recent_activity.map((day, idx) => (
            <div key={idx} className="activity-bar-container">
              <div 
                className="activity-bar"
                style={{ height: `${(day.count / getMaxActivity()) * 100}%` }}
              >
                <span className="activity-count">{day.count}</span>
              </div>
              <span className="activity-date">{day.date.slice(5)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="dashboard-row">
        {/* 소스 타입 분포 */}
        <div className="chart-section glass-card">
          <h2>📁 소스 타입 분포</h2>
          <div className="source-list">
            {stats.sources.map((src, idx) => (
              <div key={idx} className="source-item">
                <div className="source-header">
                  <span className="source-icon">{getSourceIcon(src.source_type)}</span>
                  <span className="source-name">{src.source_type}</span>
                  <span className="source-count">{src.count}</span>
                </div>
                <div className="source-bar-bg">
                  <div 
                    className="source-bar" 
                    style={{ width: `${src.percentage}%` }}
                  ></div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* 인기 태그 */}
        <div className="chart-section glass-card">
          <h2>🏷️ 인기 태그</h2>
          <div className="tag-cloud">
            {stats.top_tags.length > 0 ? (
              stats.top_tags.map((tag, idx) => (
                <span 
                  key={idx} 
                  className="tag-item"
                  style={{ fontSize: `${Math.max(0.8, Math.min(1.5, 0.8 + tag.count * 0.1))}rem` }}
                >
                  #{tag.tag} <span className="tag-count">({tag.count})</span>
                </span>
              ))
            ) : (
              <p className="no-tags">아직 태그가 없습니다</p>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
