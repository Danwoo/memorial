import { Bot, BookOpen, FileText, GitBranch } from 'lucide-react'
import type { BriefingData } from '../../types'
import type { SocratesChatContext } from '../../hooks/useSocratesChat'
import '../SocratesView.css'

const CONTEXT_CONFIG: Record<string, { tagline: string; icon: typeof Bot; suggestions: string[] }> = {
  diary: {
    tagline: '일기를 쓰면서 함께 생각을 정리해보세요',
    icon: BookOpen,
    suggestions: [
      '오늘 쓴 내용에 대해 깊이 생각해보고 싶어',
      '일기에서 반복되는 패턴이 있을까?',
      '오늘의 감정을 정리해줘',
    ],
  },
  scrap: {
    tagline: '스크랩 내용을 함께 탐구해보세요',
    icon: FileText,
    suggestions: [
      '이 스크랩의 핵심 인사이트를 분석해줘',
      '관련된 다른 스크랩이 있을까?',
      '이 내용에 대한 반론을 생각해봐줘',
    ],
  },
  mindmap: {
    tagline: '지식의 연결을 함께 탐색해보세요',
    icon: GitBranch,
    suggestions: [
      '이 노드들 사이의 관계를 분석해줘',
      '여기서 발견할 수 있는 패턴이 있을까?',
      '이 주제를 더 깊이 파고들어보자',
    ],
  },
}

interface SocratesEmptyStateProps {
  briefing: BriefingData | null
  hasBriefingContent: boolean
  onSuggestedQuestion: (text: string) => void
  context?: SocratesChatContext
}

export default function SocratesEmptyState({ briefing, hasBriefingContent, onSuggestedQuestion, context }: SocratesEmptyStateProps) {
  const ctxConfig = context ? CONTEXT_CONFIG[context.type] : null
  const Icon = ctxConfig?.icon ?? Bot
  const tagline = ctxConfig?.tagline ?? '당신의 기억을 아는 지적 동반자'

  return (
    <div className="socrates-empty">
      <div className="socrates-empty-branding">
        <Icon size={56} className="socrates-empty-icon" />
        <h2 className="socrates-empty-title">Socrates</h2>
        <p className="socrates-empty-tagline">{tagline}</p>
      </div>
      {!ctxConfig && hasBriefingContent && briefing && (
        <div className="socrates-empty-briefing">
          <p>오늘 {briefing.today_scraps?.count}개의 스크랩이 쌓였습니다</p>
          {(briefing.today_scraps?.topics?.length ?? 0) > 0 && (
            <div className="welcome-stats">
              {(briefing.today_scraps?.topics ?? []).map((t, i) => (
                <span key={i} className="welcome-topic-tag">#{t}</span>
              ))}
            </div>
          )}
        </div>
      )}

      <div className="suggested-questions">
        {ctxConfig ? (
          ctxConfig.suggestions.map((q, i) => (
            <button key={i} className="suggested-q" onClick={() => onSuggestedQuestion(q)}>
              {q}
            </button>
          ))
        ) : (
          <>
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
          </>
        )}
      </div>
    </div>
  )
}
