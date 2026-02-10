import { get } from './client'

interface GraphApiResponse {
  nodes: {
    id: string
    label: string
    properties: Record<string, unknown>
    name?: string
    group?: string
    val?: number
  }[]
  links: {
    source: string
    target: string
    type: string
  }[]
}

/** Fetch knowledge graph data */
export function fetchGraph(limit = 300): Promise<GraphApiResponse> {
  return get<GraphApiResponse>(`/graph?limit=${limit}`)
}
