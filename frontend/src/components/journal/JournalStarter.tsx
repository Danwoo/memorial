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
    <div className="journal-starter">
      <div className="journal-starter__section">
        <span className="journal-starter__label">템플릿 선택</span>
        <div className="journal-template-chips">
          {templates.map((t) => (
            <button
              key={t.id}
              className="journal-template-chip"
              onClick={() => onSelectTemplate(t.content)}
              type="button"
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      {isLoadingStarter ? (
        <div className="journal-starter__loading">
          <Loader2 size={16} className="spin" />
          회고 질문 생성 중...
        </div>
      ) : starterQuestions.length > 0 ? (
        <div className="journal-starter__section">
          <span className="journal-starter__label">오늘의 회고 질문</span>
          <div className="journal-starter-questions">
            {starterQuestions.map((q, i) => (
              <button
                key={i}
                className="journal-starter-question"
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
          className="journal-starter__cta"
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
