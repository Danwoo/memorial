import { BookOpen, FileText, GitBranch } from 'lucide-react'
import type { BriefingData, AgentType } from '../../types'
import { AGENT_CONFIG } from '../../types'
import type { SocratesChatContext } from '../../hooks/useSocratesChat'
import '../SocratesView.css'

const CONTEXT_SUGGESTIONS: Record<string, string[]> = {
  diary: [
    '오늘 쓴 내용에 대해 깊이 생각해보고 싶어',
    '일기에서 반복되는 패턴이 있을까?',
    '오늘의 감정을 정리해줘',
  ],
  scrap: [
    '이 스크랩의 핵심 인사이트를 분석해줘',
    '관련된 다른 스크랩이 있을까?',
    '스크랩 간 연결을 찾아줘',
  ],
  mindmap: [
    '이 노드들 사이의 관계를 분석해줘',
    '여기서 발견할 수 있는 패턴이 있을까?',
    '이 주제를 더 깊이 파고들어보자',
  ],
}

const CONTEXT_ICONS: Record<string, typeof BookOpen> = {
  diary: BookOpen,
  scrap: FileText,
  mindmap: GitBranch,
}

const AGENT_SUGGESTIONS: Record<AgentType, string[]> = {
  socrates: [
    '오늘 하루 감정을 탐색해보고 싶어',
    '내 생각의 전제를 분석해줘',
    '5 Whys로 근본 원인을 찾아보자',
  ],
  librarian: [
    '저장한 글 중 인상적인 것은?',
    '스크랩 간 숨겨진 연결을 찾아줘',
    '최근 저장한 내용을 요약해줘',
  ],
  oracle: [
    '최근 관심사에 대해 이야기해줘',
    '저장한 글 중 인상적인 것은?',
    '지금 가장 궁금한 것을 물어봐',
  ],
}

interface SocratesEmptyStateProps {
  briefing: BriefingData | null
  hasBriefingContent: boolean
  onSuggestedQuestion: (text: string) => void
  context?: SocratesChatContext
  agentType?: AgentType
}

export default function SocratesEmptyState({
  briefing,
  hasBriefingContent,
  onSuggestedQuestion,
  context,
  agentType = 'oracle',
}: SocratesEmptyStateProps) {
  const agentCfg = AGENT_CONFIG[agentType]

  // 컨텍스트가 있으면 컨텍스트 기반 아이콘/태그라인 사용, 없으면 에이전트 설정 사용
  const ContextIcon = context ? CONTEXT_ICONS[context.type] : null
  const displayIcon = agentCfg.icon
  const tagline = context ? agentCfg.tagline : agentCfg.tagline
  const suggestions = context
    ? CONTEXT_SUGGESTIONS[context.type] ?? AGENT_SUGGESTIONS[agentType]
    : AGENT_SUGGESTIONS[agentType]

  return (
    <div className="socrates-empty">
      <div className="socrates-empty-branding">
        {ContextIcon ? (
          <ContextIcon size={56} className="socrates-empty-icon" />
        ) : (
          <span className="socrates-empty-icon-emoji" style={{ fontSize: '3.5rem', lineHeight: 1 }}>
            {displayIcon}
          </span>
        )}
        <h2 className="socrates-empty-title">{agentCfg.label}</h2>
        <p className="socrates-empty-tagline">{tagline}</p>
      </div>

      {!context && hasBriefingContent && briefing && agentType === 'oracle' && (
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
        {suggestions.map((q, i) => (
          <button key={i} className="suggested-q" onClick={() => onSuggestedQuestion(q)}>
            {q}
          </button>
        ))}
        {!context && agentType === 'oracle' && briefing?.suggested_question && (
          <button className="suggested-q" onClick={() => onSuggestedQuestion(briefing.suggested_question)}>
            {briefing.suggested_question}
          </button>
        )}
      </div>
    </div>
  )
}
