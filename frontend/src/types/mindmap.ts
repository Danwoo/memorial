/** Properties attached to a mindmap node */
export interface MindmapNodeProperties {
  title?: string
  summary?: string
  tags?: string[]
  name?: string
  source_type?: string
  created_at?: string
  [key: string]: unknown
}

/** A node in the knowledge mindmap */
export interface MindmapNode {
  id: string
  label: string
  group?: string
  properties: MindmapNodeProperties
  val?: number
  color?: string
  name?: string
  x?: number
  y?: number
  z?: number
}

/** A link (edge) between two mindmap nodes */
export interface MindmapLink {
  source: string | MindmapNode
  target: string | MindmapNode
  type: string
}

/** Complete mindmap data structure */
export interface MindmapData {
  nodes: MindmapNode[]
  links: MindmapLink[]
}

/** 클러스터 정보 */
export interface ClusterInfo {
  cluster_id: number
  entities: string[]
  entity_types: string[]
  size: number
  summary: string
}

/** 태그 트렌드 항목 */
export interface TrendItem {
  tag: string
  counts: number[]
  direction: 'up' | 'down' | 'stable'
}

/** 고립 노드 */
export interface IsolatedNode {
  name: string
  type: string
}

/** 허브 노드 */
export interface HubNode {
  name: string
  type: string
  degree: number
}

/** 마인드맵 인사이트 전체 응답 */
export interface MindmapInsights {
  clusters: ClusterInfo[]
  trends: TrendItem[]
  isolated_nodes: IsolatedNode[]
  hub_nodes: HubNode[]
}
