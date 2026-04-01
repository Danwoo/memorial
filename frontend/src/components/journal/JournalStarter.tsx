import { Loader2, Sparkles } from 'lucide-react'

interface Template {
  id: string
  label: string
  content: string
}

interface JournalStarterProps {
  templates: Template[]
  starterQuestions: string[]
  isLoadingStarter: boolean
  onSelectTemplate: (content: string) => void
  onStarterQuestion: (question: string) => void
  onAskAI: () => void
}

export function JournalStarter({
  templates,
  starterQuestions,
  isLoadingStarter,
  onSelectTemplate,
  onStarterQuestion,
  onAskAI,
}: JournalStarterProps) {
  return (
    <div className="diary-starter">
      <div className="diary-starter__section">
        <span className="diary-starter__label">템플릿 선택</span>
        <div className="diary-template-chips">
          {templates.map((t) => (
            <button
              key={t.id}
              className="diary-template-chip"
              onClick={() => onSelectTemplate(t.content)}
              type="button"
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {isLoadingStarter ? (
        <div className="diary-starter__loading">
          <Loader2 size={16} className="spin" />
          회고 질문 생성 중...
        </div>
      ) : starterQuestions.length > 0 ? (
        <div className="diary-starter__section">
          <span className="diary-starter__label">오늘의 성찰 질문</span>
          <div className="diary-starter-questions">
            {starterQuestions.map((q, i) => (
              <button
                key={i}
                className="diary-starter-question"
                onClick={() => onStarterQuestion(q)}
                type="button"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      ) : (
        <button
          className="diary-starter__cta"
          onClick={onAskAI}
          disabled={isLoadingStarter}
          type="button"
        >
          <Sparkles size={16} />
          AI에게 질문받기
        </button>
      )}
    </div>
  )
}
