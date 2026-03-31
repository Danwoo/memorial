import { useState, useCallback, useEffect, useMemo } from 'react'
import { useResizePanel } from '../hooks/useResizePanel'
import { useNavigate } from 'react-router-dom'
import { demoPath } from '../utils/demoPath'
import type { StreakData, StatsData, ActivityData, BriefingData, DailyInsight } from '../types'
import type { DiaryDateInfo } from '../types/diary'
import { fetchStreak, fetchStats, fetchActivity, fetchBriefing, fetchDailyInsights, fetchDiaryDates } from '../api'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import { useViewCache } from '../hooks/useViewCache'
import { CACHE_KEYS } from '../utils/viewCache'
import {
  BookOpen, Lightbulb, Pencil, Sparkles, Network, Bot,
  ChevronLeft, ChevronRight,
} from 'lucide-react'
import MonthlyCalendar from './calendar/MonthlyCalendar'
import StreakBadge from './calendar/StreakBadge'
import DayDetailPanel from './calendar/DayDetailPanel'
import EmptyState from './EmptyState'
import OnboardingWizard from './OnboardingWizard'
import './CalendarView.css'

const ONBOARDING_KEY = 'memoir:onboarded'
const LEGACY_ONBOARDING_KEY = 'onboarding_completed'
const FIRST_USE_KEY = 'memoir:first-use'

function isFirstWeek(): boolean {
  let first = localStorage.getItem(FIRST_USE_KEY)
  if (!first) {
    first = new Date().toISOString()
    localStorage.setItem(FIRST_USE_KEY, first)
  }
  const days = (Date.now() - new Date(first).getTime()) / (1000 * 60 * 60 * 24)
  return days < 7
}

const ONBOARDING_SLIDES = [
  {
    icon: <Sparkles size={36} />,
    iconBg: 'rgba(99, 102, 241, 0.1)',
    iconColor: '#6366f1',
    title: 'Memoir에 오신 것을 환영합니다',
    description: '당신의 지식과 기억을 AI와 함께 관리하세요.\n매일의 생각, 읽은 글, 떠오르는 아이디어를 한 곳에 모아 정리해드립니다.',
  },
  {
    icon: <Pencil size={36} />,
    iconBg: 'rgba(99, 102, 241, 0.1)',
    iconColor: '#6366f1',
    title: '다이어리로 매일을 기록하세요',
    description: '일기를 쓰면 AI가 패턴을 분석하고,\nSocrates와 대화하며 더 깊은 성찰을 도와줍니다.',
  },
  {
    icon: <BookOpen size={36} />,
    iconBg: 'rgba(52, 211, 153, 0.1)',
    iconColor: '#34d399',
    title: '스크랩으로 지식을 모으세요',
    description: '웹 글, PDF, 메모를 저장하면\nAI가 자동으로 핵심을 추출하고 연결 관계를 파악합니다.',
  },
  {
    icon: <Network size={36} />,
    iconBg: 'rgba(96, 165, 250, 0.1)',
    iconColor: '#60a5fa',
    title: '마인드맵과 캘린더로 한눈에',
    description: '지식 간의 연결을 마인드맵으로 시각화하고,\n캘린더에서 활동 기록과 AI 인사이트를 확인하세요.',
  },
]

function getGreeting(): string {
  const hour = new Date().getHours()
  if (hour < 6) return '새벽이에요'
  if (hour < 12) return '좋은 아침이에요'
  if (hour < 18) return '좋은 오후예요'
  return '좋은 저녁이에요'
}

function getBannerMessage(briefing: BriefingData | null): string | null {
  if (!briefing) return null
  const { today_scraps, connection_hint } = briefing
  if (connection_hint) return connection_hint
  if ((today_scraps?.count ?? 0) > 0) {
    const topics = (today_scraps?.topics ?? []).slice(0, 2).join(', ')
    return topics
      ? `오늘 ${topics} 관련 스크랩 ${today_scraps?.count}개가 저장됐어요`
      : `오늘 스크랩 ${today_scraps?.count}개가 저장됐어요`
  }
  return null
}

interface CalendarCache {
  briefing: BriefingData | null
  streak: StreakData | null
  stats: StatsData | null
  activity: ActivityData[]
  dailyInsights: DailyInsight[]
  journalDates: DiaryDateInfo[]
}

export default function CalendarView() {
  const { user } = useAuth()
  const toast = useToast()
  const navigate = useNavigate()

  const { data: dashData, isLoading: loading } = useViewCache<CalendarCache>({
    key: CACHE_KEYS.DASHBOARD,
    fetcher: async () => {
      try {
        const [briefingData, streakData, statsData, activityData, insightsData, journalDatesData] = await Promise.all([
          fetchBriefing().catch(() => null),
          fetchStreak().catch(() => null),
          fetchStats().catch(() => null),
          fetchActivity(365).catch(() => ({ activity: [] })),
          fetchDailyInsights().catch(() => ({ insights: [] })),
          fetchDiaryDates(365).catch(() => ({ dates: [] })),
        ])
        return {
          briefing: briefingData,
          streak: streakData,
          stats: statsData,
          activity: activityData.activity,
          dailyInsights: insightsData.insights,
          journalDates: journalDatesData.dates,
        }
      } catch (err) {
        console.error('캘린더 데이터 로딩 실패:', err)
        toast.error('캘린더 데이터를 불러오지 못했습니다')
        throw err
      }
    },
  })

  const briefing = dashData?.briefing ?? null
  const streak = dashData?.streak ?? null
  const activity = dashData?.activity ?? []
  const dailyInsights = dashData?.dailyInsights ?? []
  const journalDates = dashData?.journalDates ?? []

  // 캘린더 월 상태
  const now = new Date()
  const [calYear, setCalYear] = useState(now.getFullYear())
  const [calMonth, setCalMonth] = useState(now.getMonth())

  // 선택된 날짜 (DayDetailPanel 토글)
  const [selectedDate, setSelectedDate] = useState<string | null>(null)
  const { vw: calPanelVw, onMouseDown: onCalPanelResize } = useResizePanel(22, 15, 40, 'left', 'calendar-panel-vw')

  const handleMonthChange = useCallback((year: number, month: number) => {
    setCalYear(year)
    setCalMonth(month)
  }, [])

  const handleDateClick = useCallback((dateStr: string) => {
    setSelectedDate(prev => prev === dateStr ? null : dateStr)
  }, [])

  const handlePanelClose = useCallback(() => {
    setSelectedDate(null)
  }, [])

  const handleNavigateJournal = useCallback((date: string) => {
    navigate(demoPath('/diary'), { state: { date } })
  }, [navigate])

  const handleNavigateMemory = useCallback((memoryId: string) => {
    navigate(demoPath('/scraps'), { state: { openMemoryId: memoryId } })
  }, [navigate])

  const handleInsightClick = useCallback((path: string) => {
    navigate(path)
  }, [navigate])

  // 캘린더 키보드 월 네비게이션 (←/→: 이전/다음 달, t: 오늘)
  const handleKeyNav = useCallback((e: KeyboardEvent) => {
    const tag = (e.target as HTMLElement).tagName
    if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT') return
    // 모달/오버레이가 열려있으면 무시
    if (document.querySelector('[role="dialog"]')) return
    if (e.key === 'ArrowLeft') {
      e.preventDefault()
      setCalYear(y => calMonth === 0 ? y - 1 : y)
      setCalMonth(m => m === 0 ? 11 : m - 1)
    } else if (e.key === 'ArrowRight') {
      e.preventDefault()
      setCalYear(y => calMonth === 11 ? y + 1 : y)
      setCalMonth(m => m === 11 ? 0 : m + 1)
    } else if (e.key === 't' || e.key === 'T') {
      const n = new Date()
      setCalYear(n.getFullYear())
      setCalMonth(n.getMonth())
    }
  }, [calMonth])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyNav)
    return () => window.removeEventListener('keydown', handleKeyNav)
  }, [handleKeyNav])

  const displayName = user?.full_name?.split(' ')[0] || user?.email?.split('@')[0] || ''

  // 온보딩 위자드
  const [showOnboarding, setShowOnboarding] = useState(
    () => !localStorage.getItem(ONBOARDING_KEY) && !localStorage.getItem(LEGACY_ONBOARDING_KEY),
  )
  const [showInteractiveWizard, setShowInteractiveWizard] = useState(false)
  const [slideIndex, setSlideIndex] = useState(0)
  const [neverShow, setNeverShow] = useState(true)

  // 사이드바 ? 버튼으로 온보딩 재오픈
  useEffect(() => {
    const handler = () => {
      setSlideIndex(0)
      setShowOnboarding(true)
    }
    window.addEventListener('memoir:show-onboarding', handler)
    return () => window.removeEventListener('memoir:show-onboarding', handler)
  }, [])

  const dismissOnboarding = useCallback((startWizard = false) => {
    if (neverShow) {
      localStorage.setItem(ONBOARDING_KEY, '1')
    }
    setShowOnboarding(false)
    if (startWizard) {
      setShowInteractiveWizard(true)
    }
  }, [neverShow])

  const isLastSlide = slideIndex === ONBOARDING_SLIDES.length - 1

  // 이번 주 요약 (일정 관리자용) — hooks must be before any conditional return
  const thisWeekSummary = useMemo(() => {
    const today = new Date()
    const dayOfWeek = today.getDay()
    const monday = new Date(today)
    monday.setDate(today.getDate() - (dayOfWeek === 0 ? 6 : dayOfWeek - 1))
    monday.setHours(0, 0, 0, 0)
    const mondayStr = monday.toISOString().slice(0, 10)
    const todayStr = today.toISOString().slice(0, 10)
    const diaryData = dashData?.journalDates ?? []
    const activityData = dashData?.activity ?? []
    const diaryCount = diaryData.filter(d => d.date >= mondayStr && d.date <= todayStr).length
    const activityCount = activityData.filter(a => a.date >= mondayStr && a.date <= todayStr && a.count > 0).length
    return { diaryCount, activityCount, daysElapsed: dayOfWeek === 0 ? 7 : dayOfWeek }
  }, [dashData])

  if (showOnboarding) {
    const slide = ONBOARDING_SLIDES[slideIndex]
    return (
      <div className="calendar-view">
        <div className="ob-wizard">
          <div className="ob-slide" key={slideIndex}>
            <div className="ob-slide-icon" style={{ background: slide.iconBg, color: slide.iconColor }}>
              {slide.icon}
            </div>
            <h2 className="ob-slide-title">{slide.title}</h2>
            <p className="ob-slide-desc">{slide.description}</p>
          </div>

          <div className="ob-dots">
            {ONBOARDING_SLIDES.map((_, i) => (
              <button
                key={i}
                className={`ob-dot ${i === slideIndex ? 'ob-dot--active' : ''}`}
                onClick={() => setSlideIndex(i)}
                aria-label={`슬라이드 ${i + 1}`}
              />
            ))}
          </div>

          {slideIndex > 0 && (
            <button className="ob-arrow ob-arrow--prev" onClick={() => setSlideIndex(i => i - 1)} aria-label="이전">
              <ChevronLeft size={20} />
            </button>
          )}
          {!isLastSlide && (
            <button className="ob-arrow ob-arrow--next" onClick={() => setSlideIndex(i => i + 1)} aria-label="다음">
              <ChevronRight size={20} />
            </button>
          )}

          <div className="ob-footer">
            <label className="ob-never-show">
              <input
                type="checkbox"
                checked={neverShow}
                onChange={e => setNeverShow(e.target.checked)}
              />
              <span>다시 보지 않기</span>
            </label>
            <div className="ob-actions">
              <button className="ob-btn-skip" onClick={() => dismissOnboarding(false)}>
                건너뛰기
              </button>
              {isLastSlide ? (
                <button className="ob-btn-start" onClick={() => dismissOnboarding(true)}>
                  시작하기
                </button>
              ) : (
                <button className="ob-btn-next" onClick={() => setSlideIndex(i => i + 1)}>
                  다음
                </button>
              )}
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (showInteractiveWizard) {
    return (
      <div className="calendar-view">
        <OnboardingWizard onComplete={() => {
          setShowInteractiveWizard(false)
          toast.success('준비 완료! 이제 Memoir를 자유롭게 사용해보세요 🎉')
        }} />
      </div>
    )
  }

  if (loading) {
    return (
      <div className="calendar-view">
        <div className="skeleton skeleton-title" style={{ width: '60%' }} />
        <div className="skeleton skeleton-card" style={{ height: 80 }} />
        <div className="skeleton skeleton-card" style={{ height: 400 }} />
      </div>
    )
  }

  const bannerMsg = getBannerMessage(briefing)

  return (
    <div className="calendar-view">
      {/* 슬림 배너 */}
      <div className="calendar-banner">
        <div className="banner-greeting">
          <h1>{getGreeting()}{displayName ? `, ${displayName}님` : ''}</h1>
          {bannerMsg && (
            <span className="banner-insight">{bannerMsg}</span>
          )}
        </div>
        <button
          className="banner-diary-cta"
          onClick={() => navigate(demoPath('/diary'))}
          type="button"
        >
          <Pencil size={14} />
          오늘 다이어리 쓰기
        </button>
        {briefing?.suggested_question && (
          <button
            className="banner-question"
            onClick={() => navigate(demoPath('/diary'), { state: { prefillQuestion: briefing.suggested_question } })}
          >
            <Lightbulb size={16} className="banner-question-icon" />
            <span className="banner-question-text">{briefing.suggested_question}</span>
          </button>
        )}
      </div>

      {/* 퀵 액션 카드 (첫 주 또는 활동/기록 적을 때) */}
      {(isFirstWeek() || journalDates.length < 3 || !dashData?.stats || (dashData.stats.overview?.total_scraps ?? 0) < 10) && (
        <div className="calendar-quick-actions">
          <button className="quick-action-card" onClick={() => navigate(demoPath('/diary'))}>
            <Pencil size={20} />
            <div className="quick-action-text">
              <span className="quick-action-title">다이어리 쓰기</span>
              <span className="quick-action-desc">오늘의 생각을 기록하세요</span>
            </div>
          </button>
          <button className="quick-action-card" onClick={() => navigate(demoPath('/scraps'))}>
            <BookOpen size={20} />
            <div className="quick-action-text">
              <span className="quick-action-title">스크랩 추가</span>
              <span className="quick-action-desc">웹 글이나 메모를 저장하세요</span>
            </div>
          </button>
          <button className="quick-action-card" onClick={() => navigate(demoPath('/diary'), { state: { openSocrates: true } })}>
            <Bot size={20} />
            <div className="quick-action-text">
              <span className="quick-action-title">AI 대화 (Socrates)</span>
              <span className="quick-action-desc">AI와 오늘 하루를 돌아보세요</span>
            </div>
          </button>
        </div>
      )}

      {/* 이번 주 요약 (활동이 있을 때만 표시) */}
      {journalDates.length > 0 && (
        <div className="calendar-week-summary">
          <span className="week-summary-label">이번 주</span>
          <span className="week-summary-item">
            📝 다이어리 <strong>{thisWeekSummary.diaryCount}</strong>/{thisWeekSummary.daysElapsed}일
          </span>
          <span className="week-summary-item">
            📌 기록한 날 <strong>{thisWeekSummary.activityCount}</strong>일
          </span>
        </div>
      )}

      {/* 빈 상태: 기록이 전혀 없을 때 */}
      {!loading && journalDates.length === 0 && activity.length === 0 && (
        <EmptyState
          icon={<Pencil size={32} />}
          title="아직 기록이 없습니다"
          description="첫 다이어리를 작성하거나 스크랩을 저장하면 여기에 활동이 나타납니다."
          ctaLabel="첫 다이어리 쓰기"
          onCtaClick={() => navigate(demoPath('/diary'))}
        />
      )}

      {/* 캘린더 + DayDetailPanel */}
      <div className={`calendar-main-container${selectedDate ? ' calendar-main-container--panel-open' : ''}`}>
        <div
          className="calendar-main-main"
          style={selectedDate ? { marginRight: `${calPanelVw}vw` } : undefined}
        >
          <MonthlyCalendar
            year={calYear}
            month={calMonth}
            journalDates={journalDates}
            activityData={activity}
            onDateClick={handleDateClick}
            onMonthChange={handleMonthChange}
            selectedDate={selectedDate}
            streakBadge={streak ? <StreakBadge streak={streak} /> : undefined}
          />
          <div className="calendar-keyboard-hint">
            <kbd>←</kbd><kbd>→</kbd> 월 이동 &nbsp;·&nbsp; <kbd>T</kbd> 오늘
          </div>
        </div>
        {selectedDate && (
          <DayDetailPanel
            date={selectedDate}
            onClose={handlePanelClose}
            onNavigateJournal={handleNavigateJournal}
            onNavigateMemory={handleNavigateMemory}
            panelWidth={`${calPanelVw}vw`}
            onPanelResize={onCalPanelResize}
            dailyInsights={dailyInsights}
            onInsightClick={handleInsightClick}
          />
        )}
      </div>
    </div>
  )
}
