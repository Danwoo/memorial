// 노드 타입별 색상 팔레트
export const NODE_COLORS: Record<string, string> = {
  Memory: '#a78bfa',
  Entity: '#34d399',
  Concept: '#60a5fa',
  Person: '#f472b6',
  Organization: '#fb923c',
  Company: '#fb923c',
  Technology: '#22d3ee',
  Platform: '#a3e635',
  Product: '#e879f9',
  Location: '#fbbf24',
  Event: '#f87171',
  Topic: '#818cf8',
  Idea: '#818cf8',
  Framework: '#22d3ee',
  Language: '#60a5fa',
  Tool: '#34d399',
  default: '#9ca3af',
}

// 노드 타입 한국어 매핑
export const NODE_TYPE_KO: Record<string, string> = {
  Memory: '메모리',
  Entity: '엔티티',
  Concept: '개념',
  Person: '인물',
  Organization: '조직',
  Company: '회사',
  Technology: '기술',
  Platform: '플랫폼',
  Product: '제품',
  Location: '장소',
  Event: '이벤트',
  Topic: '주제',
  Idea: '아이디어',
  Framework: '프레임워크',
  Language: '언어',
  Tool: '도구',
}

// 관계 타입 한국어 매핑
export const LINK_TYPE_KO: Record<string, string> = {
  RELATED_TO: '관련',
  RELATES_TO: '관련',
  MENTIONED_IN: '언급됨',
  MENTIONS: '언급',
  HAS_TAG: '태그',
  HAS_ENTITY: '엔티티 포함',
  ASSOCIATED_WITH: '연관',
  PART_OF: '소속',
  CAUSED_BY: '원인',
  WORKS_AT: '근무',
  LOCATED_IN: '위치',
  CREATED_BY: '작성자',
  USED_BY: '사용자',
  USED_IN: '사용됨',
  USED_FOR: '용도',
  USES: '사용',
  SIMILAR_TO: '유사',
  OPPOSITE_OF: '반대',
  DEPENDS_ON: '의존',
  DERIVED_FROM: '파생',
  CONTAINS: '포함',
  BELONGS_TO: '소속',
  HAS: '보유',
  IS_A: '분류',
  BUILT_WITH: '구축',
  INSPIRED_BY: '영감',
}

// 한국어 변환 헬퍼
export function toKo(type: string, map: Record<string, string>): string {
  return map[type] || type
}
