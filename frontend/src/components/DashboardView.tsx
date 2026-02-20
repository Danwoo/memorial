import { useEffect, useState } from 'react'
import type { StreakData, StatsData, ActivityData, BriefingData, DailyInsight } from '../types'
import type { ReportData } from '../api/reports'
import { fetchStreak, fetchStats, fetchActivity, fetchBriefing, fetchDailyInsights, fetchWeeklyReport, fetchMonthlyReport } from '../api'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import BriefingTab from './dashboard/BriefingTab'
import ReportTab from './dashboard/ReportTab'
import './DashboardView.css'

type DashboardTab = 'briefing' | 'weekly' | 'monthly'

export default function DashboardView() {
  const { user } = useAuth()
  const toast = useToast()

  const [activeTab, setActiveTab] = useState<DashboardTab>('briefing')
  const [briefing, setBriefing] = useState<BriefingData | null>(null)
  const [streak, setStreak] = useState<StreakData | null>(null)
  const [stats, setStats] = useState<StatsData | null>(null)
  const [activity, setActivity] = useState<ActivityData[]>([])
  const [dailyInsights, setDailyInsights] = useState<DailyInsight[]>([])
  const [loading, setLoading] = useState(true)
  const [weeklyReport, setWeeklyReport] = useState<ReportData | null>(null)
  const [monthlyReport, setMonthlyReport] = useState<ReportData | null>(null)
  const [reportLoading, setReportLoading] = useState(false)

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

  useEffect(() => {
    if (activeTab === 'weekly' && !weeklyReport) {
      setReportLoading(true)
      fetchWeeklyReport()
        .then(setWeeklyReport)
        .catch(() => toast.error('주간 리포트를 불러오지 못했습니다'))
        .finally(() => setReportLoading(false))
    } else if (activeTab === 'monthly' && !monthlyReport) {
      setReportLoading(true)
      fetchMonthlyReport()
        .then(setMonthlyReport)
        .catch(() => toast.error('월간 리포트를 불러오지 못했습니다'))
        .finally(() => setReportLoading(false))
    }
  }, [activeTab, weeklyReport, monthlyReport, toast])

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
      {/* 탭 네비게이션 */}
      <div className="dashboard-tabs">
        <button
          className={`dashboard-tab ${activeTab === 'briefing' ? 'active' : ''}`}
          onClick={() => setActiveTab('briefing')}
        >
          오늘 브리핑
        </button>
        <button
          className={`dashboard-tab ${activeTab === 'weekly' ? 'active' : ''}`}
          onClick={() => setActiveTab('weekly')}
        >
          주간 리포트
        </button>
        <button
          className={`dashboard-tab ${activeTab === 'monthly' ? 'active' : ''}`}
          onClick={() => setActiveTab('monthly')}
        >
          월간 리포트
        </button>
      </div>

      {activeTab !== 'briefing' ? (
        <ReportTab
          report={activeTab === 'weekly' ? weeklyReport : monthlyReport}
          loading={reportLoading}
        />
      ) : (
        <BriefingTab
          displayName={displayName}
          briefing={briefing}
          streak={streak}
          stats={stats}
          activity={activity}
          dailyInsights={dailyInsights}
        />
      )}
    </div>
  )
}
