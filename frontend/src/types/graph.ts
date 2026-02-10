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
