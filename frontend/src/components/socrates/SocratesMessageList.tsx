import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { rehypeSanitize, sanitizeSchema } from '../../utils/markdownSanitize'
import {
  User, Bot, Paperclip, ChevronDown, ChevronUp,
  ThumbsUp, ThumbsDown,
} from 'lucide-react'
import type { SocratesMessage } from '../../types'
import SourceIcon from '../shared/SourceIcon'
import SocratesActionButtons from './SocratesActionButtons'

const INSIGHT_PATTERNS = [
  '인사이트', '정리하면', '핵심은', '결론적으로', '요약하면',
  '중요한 점', '깨달은', '발견한', '연결해보면', '통찰',
]

function shouldShowActions(
  content: string,
  messageIndex: number,
  totalMessages: number,
): boolean {
  if (content.length < 100) return false
  if (messageIndex < 2) return false
  const isRecentEnough = totalMessages - messageIndex <= 4
  if (!isRecentEnough) return false
  const hasInsightPattern = INSIGHT_PATTERNS.some(p => content.includes(p))
  return hasInsightPattern || (messageIndex >= 4 && messageIndex % 2 === 1)
}

interface SocratesMessageListProps {
  messages: SocratesMessage[]
  expandedRefs: Set<number>
  feedbacks: Map<number, 'good' | 'bad'>
  onToggleRefExpand: (idx: number) => void
  onFeedback: (msgIndex: number, rating: 'good' | 'bad') => void
  onScrapClick?: (scrapId: string) => void
  onSaveAsScrap?: (content: string) => void
  onInsertToDiary?: (content: string) => void
  isPanelMode?: boolean
}

export default function SocratesMessageList({
  messages, expandedRefs, feedbacks,
  onToggleRefExpand, onFeedback, onScrapClick,
  onSaveAsScrap, onInsertToDiary, isPanelMode = false,
}: SocratesMessageListProps) {

  return (
    <>
      {messages.map((msg, idx) => (
        <div key={idx} className={`message ${msg.role}`}>
          <div className="message-avatar">
            {msg.role === 'user' ? <User size={20} /> : <Bot size={20} />}
          </div>
          <div className="message-content">
            {msg.role === 'assistant' ? (
              msg.content ? (
                <>
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    rehypePlugins={[[rehypeSanitize, sanitizeSchema]]}
                  >
                    {msg.content}
                  </ReactMarkdown>
                  {msg.references && msg.references.length > 0 && (
                    <div className="socrates-references">
                      <button
                        className="socrates-references-toggle"
                        onClick={() => onToggleRefExpand(idx)}
                        type="button"
                      >
                        <Paperclip size={14} />
                        <span className="socrates-references-label">{msg.references.length}개 기억 참조</span>
                        <span className="socrates-references-badge">{msg.references.length}</span>
                        {expandedRefs.has(idx) ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
                      </button>
                      {expandedRefs.has(idx) && (
                        <div className="socrates-references-list">
                          {msg.references.map(ref => (
                            <button
                              key={ref.id}
                              className="socrates-reference-chip"
                              onClick={() => onScrapClick?.(ref.id)}
                              type="button"
                            >
                              <SourceIcon type={ref.source_type} size={14} />
                              <span className="socrates-reference-title">{ref.title}</span>
                              <span className="socrates-reference-date">{ref.created_at}</span>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  )}
                  <div className="socrates-feedback-buttons">
                    <button
                      type="button"
                      className={`socrates-feedback-btn${feedbacks.get(idx) === 'good' ? ' active' : ''}`}
                      onClick={() => onFeedback(idx, 'good')}
                      title="도움이 됐어요"
                    >
                      <ThumbsUp size={14} />
                    </button>
                    <button
                      type="button"
                      className={`socrates-feedback-btn${feedbacks.get(idx) === 'bad' ? ' active bad' : ''}`}
                      onClick={() => onFeedback(idx, 'bad')}
                      title="아쉬워요"
                    >
                      <ThumbsDown size={14} />
                    </button>
                  </div>
                  {shouldShowActions(msg.content, idx, messages.length) && (
                    <SocratesActionButtons
                      content={msg.content}
                      onSaveAsScrap={onSaveAsScrap}
                      onInsertToDiary={onInsertToDiary}
                      isPanelMode={isPanelMode}
                    />
                  )}
                </>
              ) : (
                <div className="typing-indicator-container">
                  <div className="typing-dots">
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                    <span className="typing-dot" />
                  </div>
                  <span className="typing-text">Socrates가 생각하고 있습니다...</span>
                </div>
              )
            ) : (
              msg.content || <span className="typing-indicator">...</span>
            )}
          </div>
        </div>
      ))}
    </>
  )
}
