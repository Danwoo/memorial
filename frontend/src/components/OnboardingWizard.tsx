import { useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { demoPath } from '../utils/demoPath'
import { BookOpen, MessageCircle, PenTool, Globe, FileText, ChevronRight, Check, Sparkles, X } from 'lucide-react'
import { useToast } from '../contexts/ToastContext'
import { createScrap } from '../api'
import './OnboardingWizard.css'

const TOTAL_STEPS = 3

interface OnboardingWizardProps {
  onComplete: () => void
}

export default function OnboardingWizard({ onComplete }: OnboardingWizardProps) {
  const [step, setStep] = useState(1)
  const [memoryAdded, setMemoryAdded] = useState(false)
  const [inputMode, setInputMode] = useState<'url' | 'note' | null>(null)
  const [inputValue, setInputValue] = useState('')
  const [isSaving, setIsSaving] = useState(false)
  const navigate = useNavigate()
  const toast = useToast()

  const handleSkip = useCallback(() => {
    onComplete()
  }, [onComplete])

  const handleNext = useCallback(() => {
    if (step < TOTAL_STEPS) {
      setStep(s => s + 1)
    } else {
      onComplete()
    }
  }, [step, onComplete])

  const handleAddMemory = useCallback(async () => {
    if (!inputValue.trim()) return
    setIsSaving(true)
    try {
      if (inputMode === 'url') {
        await createScrap({ sourceType: 'WEB', url: inputValue.trim() })
      } else {
        await createScrap({ sourceType: 'NOTE', content: inputValue.trim() })
      }
      setMemoryAdded(true)
      toast.success('첫 번째 스크랩이 저장되었습니다!')
    } catch {
      toast.error('저장에 실패했습니다. 다시 시도해주세요.')
    } finally {
      setIsSaving(false)
    }
  }, [inputMode, inputValue, toast])

  const handleQuestionClick = useCallback((question: string) => {
    onComplete()
    navigate(demoPath('/diary'), { state: { openSocrates: true, initialMessage: question } })
  }, [onComplete, navigate])

  return (
    <div className="onboarding-overlay">
      <div className="onboarding-modal">
        {/* 헤더 */}
        <div className="onboarding-header">
          <div className="onboarding-steps">
            {Array.from({ length: TOTAL_STEPS }, (_, i) => (
              <div
                key={i}
                className={`step-dot ${i + 1 === step ? 'active' : ''} ${i + 1 < step ? 'completed' : ''}`}
              />
            ))}
          </div>
          <button className="onboarding-skip" onClick={handleSkip} type="button">
            건너뛰기
          </button>
        </div>

        {/* Step 1: 환영 + 제품 소개 */}
        {step === 1 && (
          <div className="onboarding-content step-1">
            <div className="onboarding-icon-main">
              <Sparkles size={32} />
            </div>
            <h2>Memoir에 오신 것을 환영합니다!</h2>
            <p className="onboarding-subtitle">
              당신의 지식과 기억을 AI와 함께 관리하세요
            </p>

            <div className="feature-cards">
              <div className="feature-card" style={{ animationDelay: '0.1s' }}>
                <div className="feature-icon">
                  <BookOpen size={24} />
                </div>
                <h3>수집</h3>
                <p>웹에서 읽은 글을 한 곳에 모으세요</p>
              </div>
              <div className="feature-card" style={{ animationDelay: '0.2s' }}>
                <div className="feature-icon">
                  <MessageCircle size={24} />
                </div>
                <h3>대화</h3>
                <p>AI와 대화하며 기억을 탐색하세요</p>
              </div>
              <div className="feature-card" style={{ animationDelay: '0.3s' }}>
                <div className="feature-icon">
                  <PenTool size={24} />
                </div>
                <h3>회고</h3>
                <p>하루를 돌아보며 저널을 작성하세요</p>
              </div>
            </div>

            <button className="onboarding-btn-primary" onClick={handleNext} type="button">
              시작하기 <ChevronRight size={16} />
            </button>
          </div>
        )}

        {/* Step 2: 첫 메모리 추가 유도 */}
        {step === 2 && (
          <div className="onboarding-content step-2">
            <h2>먼저 스크랩을 하나 추가해볼까요?</h2>
            <p className="onboarding-subtitle">
              흥미로운 글의 URL이나 간단한 메모를 저장해보세요
            </p>

            {memoryAdded ? (
              <div className="memory-added-success">
                <div className="success-icon">
                  <Check size={32} />
                </div>
                <p>첫 번째 기억이 저장되었습니다!</p>
                <button className="onboarding-btn-primary" onClick={handleNext} type="button">
                  다음으로 <ChevronRight size={16} />
                </button>
              </div>
            ) : inputMode === null ? (
              <div className="scrap-options">
                <button
                  className="scrap-option-card"
                  onClick={() => setInputMode('url')}
                  type="button"
                >
                  <Globe size={24} />
                  <h3>URL 저장하기</h3>
                  <p>읽었던 글이나 관심 있는 웹 페이지의 URL을 입력하세요</p>
                </button>
                <button
                  className="scrap-option-card"
                  onClick={() => setInputMode('note')}
                  type="button"
                >
                  <FileText size={24} />
                  <h3>직접 입력하기</h3>
                  <p>기억하고 싶은 내용을 간단한 메모로 남기세요</p>
                </button>
              </div>
            ) : (
              <div className="memory-input-area">
                <div className="memory-input-header">
                  <span className="memory-input-type">
                    {inputMode === 'url' ? <><Globe size={14} /> URL 입력</> : <><FileText size={14} /> 메모 입력</>}
                  </span>
                  <button className="memory-input-back" onClick={() => { setInputMode(null); setInputValue('') }} type="button">
                    <X size={14} /> 취소
                  </button>
                </div>
                {inputMode === 'url' ? (
                  <input
                    className="onboarding-input"
                    type="url"
                    placeholder="https://example.com/interesting-article"
                    value={inputValue}
                    onChange={e => setInputValue(e.target.value)}
                    autoFocus
                  />
                ) : (
                  <textarea
                    className="onboarding-textarea"
                    placeholder="기억하고 싶은 내용을 적어주세요..."
                    value={inputValue}
                    onChange={e => setInputValue(e.target.value)}
                    rows={3}
                    autoFocus
                  />
                )}
                <button
                  className="onboarding-btn-primary"
                  onClick={handleAddMemory}
                  disabled={!inputValue.trim() || isSaving}
                  type="button"
                >
                  {isSaving ? '저장 중...' : '저장하기'}
                </button>
              </div>
            )}

            {!memoryAdded && (
              <button className="onboarding-btn-text" onClick={handleNext} type="button">
                나중에 하기
              </button>
            )}
          </div>
        )}

        {/* Step 3: 첫 대화 유도 */}
        {step === 3 && (
          <div className="onboarding-content step-3">
            <h2>Socrates에게 질문해보세요</h2>
            <p className="onboarding-subtitle">
              AI 비서가 저장된 기억을 바탕으로 대화해줍니다
            </p>

            <div className="question-suggestions">
              <button
                className="question-card"
                onClick={() => handleQuestionClick('최근 관심사에 대해 이야기해줘')}
                type="button"
              >
                <MessageCircle size={18} />
                <span>최근 관심사에 대해 이야기해줘</span>
                <ChevronRight size={14} />
              </button>
              <button
                className="question-card"
                onClick={() => handleQuestionClick('저장한 글 중 인상적인 것은?')}
                type="button"
              >
                <MessageCircle size={18} />
                <span>저장한 글 중 인상적인 것은?</span>
                <ChevronRight size={14} />
              </button>
              <button
                className="question-card"
                onClick={() => handleQuestionClick('이번 주 내가 읽은 것들을 정리해줘')}
                type="button"
              >
                <MessageCircle size={18} />
                <span>이번 주 내가 읽은 것들을 정리해줘</span>
                <ChevronRight size={14} />
              </button>
            </div>

            <button className="onboarding-btn-primary" onClick={handleNext} type="button">
              완료 <Check size={16} />
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
