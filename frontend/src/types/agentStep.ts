// frontend/src/types/agentStep.ts
export type AgentStepStatus = 'pending' | 'active' | 'done' | 'error';

export interface AgentStep {
  id: string;
  tool: string;
  label: string;
  status: AgentStepStatus;
  detail?: string;
  startedAt: number;
  endedAt?: number;
}

export const TOOL_LABELS: Record<string, string> = {
  search_diaries: '일기 검색',
  get_diary_detail: '일기 상세 조회',
  get_emotion_trend: '감정 추세 분석',
  search_past_conversations: '이전 대화 검색',
  generate_reflection_questions: '성찰 질문 생성',
  detect_cognitive_distortions: '인지 왜곡 분석',
  generate_diary_draft: '일기 초안 생성',
  search_scraps: '스크랩 검색',
  search_graph_entities: '그래프 엔티티 검색',
  get_graph_context: '그래프 컨텍스트 조회',
  get_community_insights: '커뮤니티 인사이트',
  find_connections: '연결점 탐색',
  compare_content: '콘텐츠 비교',
  get_entity_timeline: '엔티티 타임라인',
  get_emotion_trend_analysis: '감정 트렌드 분석',
  delegate_to_librarian: 'Librarian에게 위임',
  delegate_to_analyst: 'Analyst에게 위임',
  delegate_to_curator: 'Curator에게 위임',
};

export function getToolLabel(toolName: string): string {
  return TOOL_LABELS[toolName] ?? toolName.replace(/_/g, ' ');
}
