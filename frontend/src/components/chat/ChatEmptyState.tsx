import { Bot } from 'lucide-react'
import type { BriefingData } from '../../types'

interface ChatEmptyStateProps {
  briefing: BriefingData | null
  hasBriefingContent: boolean
  onSuggestedQuestion: (text: string) => void
}

export default function ChatEmptyState({ briefing, hasBriefingContent, onSuggestedQuestion }: ChatEmptyStateProps) {
  return (
    <div className="chat-empty">
      <div className="chat-empty-branding">
        <Bot size={56} className="chat-empty-icon" />
        <h2 className="chat-empty-title">Socrates</h2>
        <p className="chat-empty-tagline">당신의 기억을 아는 지적 동반자</p>
      </div>
      {hasBriefingContent && briefing && (
        <div className="chat-empty-briefing">
          <p>오늘 {briefing.today_memories.count}개의 기억이 쌓였습니다</p>
          {briefing.today_memories.topics.length > 0 && (
            <div className="welcome-stats">
              {briefing.today_memories.topics.map((t, i) => (
                <span key={i} className="welcome-topic-tag">#{t}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="suggested-questions">
        {briefing?.suggested_question && (
          <button className="suggested-q" onClick={() => onSuggestedQuestion(briefing.suggested_question)}>
            {briefing.suggested_question}
          </button>
        )}
        <button className="suggested-q" onClick={() => onSuggestedQuestion('최근 관심사에 대해 이야기해줘')}>
          최근 관심사에 대해 이야기해줘
        </button>
        <button className="suggested-q" onClick={() => onSuggestedQuestion('저장한 글 중 인상적인 것은?')}>
          저장한 글 중 인상적인 것은?
        </button>
      </div>
    </div>
  )
}
