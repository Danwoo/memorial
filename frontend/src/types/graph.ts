/** Properties attached to a graph node */
export interface GraphNodeProperties {
  title?: string
  summary?: string
  tags?: string[]
  name?: string
  source_type?: string
  created_at?: string
  [key: string]: unknown
}

/** A node in the knowledge graph */
export interface GraphNode {
  id: string
  label: string
  group?: string
  properties: GraphNodeProperties
  val?: number
  color?: string
  name?: string
  x?: number
  y?: number
  z?: number
}

/** A link (edge) between two graph nodes */
export interface GraphLink {
  source: string | GraphNode
  target: string | GraphNode
  type: string
}

/** Complete graph data structure */
export interface GraphData {
  nodes: GraphNode[]
  links: GraphLink[]
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

/** 그래프 인사이트 전체 응답 */
export interface GraphInsights {
  clusters: ClusterInfo[]
  trends: TrendItem[]
  isolated_nodes: IsolatedNode[]
  hub_nodes: HubNode[]
}
