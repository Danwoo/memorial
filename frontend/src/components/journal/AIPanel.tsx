import { useState } from 'react'
import { ChevronDown, ChevronUp, Brain, Heart, Loader2 } from 'lucide-react'
import type { ReviewQuestionsResponse, InsightsResponse } from '../../types'
import { fetchReviewQuestions, fetchInsights } from '../../api'
import './AIPanel.css'

interface AIPanelProps {
  content: string
  onInsertQuestion: (question: string) => void
}

export function AIPanel({ content, onInsertQuestion }: AIPanelProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState<'questions' | 'insights'>('questions')
  const [questions, setQuestions] = useState<ReviewQuestionsResponse | null>(null)
  const [insights, setInsights] = useState<InsightsResponse | null>(null)
  const [isLoading, setIsLoading] = useState(false)

  const handleLoadAnalysis = async () => {
    if (!content.trim() || content.trim().length < 20) {
      alert('분석하려면 20자 이상 작성해주세요.')
      return
    }
    setIsOpen(true)
    setIsLoading(true)
    try {
      const [q, i] = await Promise.all([
        fetchReviewQuestions(content),
        fetchInsights(content),
      ])
      setQuestions(q)
      setInsights(i)
    } catch (err) {
      console.error('AI 분석 실패', err)
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className={`ai-panel ${isOpen ? 'ai-panel--open' : ''}`}>
      <button
        className="ai-panel__toggle"
        onClick={() => isOpen ? setIsOpen(false) : handleLoadAnalysis()}
        type="button"
      >
        <Brain size={16} />
        <span>AI 분석</span>
        {isOpen ? <ChevronDown size={16} /> : <ChevronUp size={16} />}
      </button>

      {isOpen && (
        <div className="ai-panel__content">
          <div className="ai-panel__tabs">
            <button
              className={`ai-panel-tab ${activeTab === 'questions' ? 'ai-panel-tab--active' : ''}`}
              onClick={() => setActiveTab('questions')}
              type="button"
            >
              성찰 질문
            </button>
            <button
              className={`ai-panel-tab ${activeTab === 'insights' ? 'ai-panel-tab--active' : ''}`}
              onClick={() => setActiveTab('insights')}
              type="button"
            >
              <Heart size={14} />
              마음 건강 체크
            </button>
          </div>

          {isLoading ? (
            <div className="ai-panel__loading">
              <Loader2 size={20} className="spin" />
              분석 중...
            </div>
          ) : activeTab === 'questions' ? (
            <div className="ai-panel__questions">
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
                <p className="ai-panel__empty">AI 분석 버튼을 눌러 성찰 질문을 생성해보세요.</p>
              )}
            </div>
          ) : (
            <div className="ai-panel__insights">
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
                    <p className="ai-panel__empty">인지 왜곡이 감지되지 않았습니다.</p>
                  )}
                </>
              ) : (
                <p className="ai-panel__empty">AI 분석 버튼을 눌러 마음 건강을 체크해보세요.</p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
