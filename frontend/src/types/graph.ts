/** A node in the knowledge graph */
export interface GraphNode {
  id: string
  label: string
  properties: Record<string, unknown>
  val?: number
  color?: string
  name?: string
  x?: number
  y?: number
  url?: string
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
