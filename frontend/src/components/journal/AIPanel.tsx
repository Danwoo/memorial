import { useState, useEffect, useRef, useCallback } from 'react'
import { Brain, Heart, Loader2, Sparkles } from 'lucide-react'
import { useToast } from '../../contexts/ToastContext'
import type { ReviewQuestionsResponse, InsightsResponse } from '../../types'
import { fetchReviewQuestions, fetchInsights } from '../../api'
import './AIPanel.css'

const MIN_CONTENT_LENGTH_FOR_ANALYSIS = 20
const AUTO_ANALYSIS_MIN_LENGTH = 100
const AUTO_ANALYSIS_DEBOUNCE_MS = 5000

interface AIPanelProps {
  content: string
  onInsertQuestion: (question: string) => void
}

export function AIPanel({ content, onInsertQuestion }: AIPanelProps) {
  const toast = useToast()
  const [activeTab, setActiveTab] = useState<'questions' | 'insights'>('questions')
  const [questions, setQuestions] = useState<ReviewQuestionsResponse | null>(null)
  const [insights, setInsights] = useState<InsightsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)
  const [isAutoWaiting, setIsAutoWaiting] = useState(false)
  const hasAutoTriggeredRef = useRef(false)

  const handleLoadAnalysis = useCallback(async () => {
    if (!content.trim() || content.trim().length < MIN_CONTENT_LENGTH_FOR_ANALYSIS) {
      toast.info(`분석하려면 ${MIN_CONTENT_LENGTH_FOR_ANALYSIS}자 이상 작성해주세요.`)
      return
    }
    setIsLoading(true)
    setIsAutoWaiting(false)
    try {
      const [q, i] = await Promise.all([
        fetchReviewQuestions(content),
        fetchInsights(content),
      ])
      setQuestions(q)
      setInsights(i)
    } catch (err) {
      console.error('AI 분석 실패', err)
      toast.error('AI 분석에 실패했습니다.')
    } finally {
      setIsLoading(false)
    }
  }, [content, toast])

  // 자동 분석: content 100자 이상 + 5초 디바운스
  useEffect(() => {
    if (hasAutoTriggeredRef.current) return
    if (questions || insights) return
    if (content.trim().length < AUTO_ANALYSIS_MIN_LENGTH) {
      setIsAutoWaiting(false)
      return
    }
    setIsAutoWaiting(true)
    const timer = setTimeout(() => {
      hasAutoTriggeredRef.current = true
      handleLoadAnalysis()
    }, AUTO_ANALYSIS_DEBOUNCE_MS)
    return () => clearTimeout(timer)
  }, [content, questions, insights, handleLoadAnalysis])

  const hasResults = questions || insights

  return (
    <div className="ai-sidebar">
      <div className="ai-sidebar__header">
        <Brain size={16} />
        <span>AI 분석</span>
      </div>

      <div className="ai-sidebar__tabs">
        <button
          className={`ai-sidebar-tab ${activeTab === 'questions' ? 'ai-sidebar-tab--active' : ''}`}
          onClick={() => setActiveTab('questions')}
          type="button"
        >
          성찰 질문
        </button>
        <button
          className={`ai-sidebar-tab ${activeTab === 'insights' ? 'ai-sidebar-tab--active' : ''}`}
          onClick={() => setActiveTab('insights')}
          type="button"
        >
          <Heart size={14} />
          마음 건강
        </button>
      </div>

      <div className="ai-sidebar__content">
        {!hasResults && !isLoading ? (
          <div className="ai-sidebar__empty">
            {isAutoWaiting ? (
              <div className="ai-sidebar__auto-waiting">
                <Loader2 size={16} className="spin" />
                <span>내용을 분석하고 있습니다...</span>
              </div>
            ) : (
              <>
                <button
                  className="ai-sidebar__analyze-btn"
                  onClick={handleLoadAnalysis}
                  type="button"
                >
                  <Sparkles size={16} />
                  AI 분석 시작
                </button>
                <p className="ai-sidebar__hint">
                  글을 작성한 후 AI 분석을 요청하면 성찰 질문과 마음 건강 체크를 받을 수 있습니다.
                  {content.trim().length < AUTO_ANALYSIS_MIN_LENGTH && (
                    <><br />100자 이상 작성 시 자동으로 분석이 시작됩니다.</>
                  )}
                </p>
              </>
            )}
          </div>
        ) : isLoading ? (
          <div className="ai-sidebar__loading">
            <Loader2 size={20} className="spin" />
            분석 중...
          </div>
        ) : activeTab === 'questions' ? (
          <div className="ai-sidebar__questions">
            {questions?.questions.length ? (
              questions.questions.map((q, i) => (
                <div key={i} className="ai-question-item">
                  <p className="ai-question-text">{q}</p>
                  <button
                    className="ai-question-insert"
                    onClick={() => onInsertQuestion(q)}
                    type="button"
                  >
                    답변 작성
                  </button>
                </div>
              ))
            ) : (
              <p className="ai-sidebar__no-result">성찰 질문이 없습니다.</p>
            )}
            <button
              className="ai-sidebar__refresh-btn"
              onClick={handleLoadAnalysis}
              disabled={isLoading}
              type="button"
            >
              <Sparkles size={14} />
              다시 분석
            </button>
          </div>
        ) : (
          <div className="ai-sidebar__insights">
            {insights ? (
              <>
                <div className="wellness-score">
                  <span className="wellness-label">웰니스 점수</span>
                  <span className="wellness-value">{insights.wellness_score}/10</span>
                </div>
                {insights.has_distortions && insights.distortions.length > 0 ? (
                  <div className="distortion-list">
                    {insights.distortions.map((d, i) => (
                      <div key={i} className="distortion-item">
                        <div className="distortion-name">{d.name}</div>
                        <div className="distortion-trigger">{d.trigger}</div>
                        <div className="distortion-feedback">{d.feedback}</div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <p className="ai-sidebar__no-result">인지 왜곡이 감지되지 않았습니다.</p>
                )}
                <button
                  className="ai-sidebar__refresh-btn"
                  onClick={handleLoadAnalysis}
                  disabled={isLoading}
                  type="button"
                >
                  <Sparkles size={14} />
                  다시 분석
                </button>
              </>
            ) : (
              <p className="ai-sidebar__no-result">마음 건강 분석 결과가 없습니다.</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
