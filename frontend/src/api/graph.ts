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

// 지식 그래프 노드 및 링크 데이터 조회
export function fetchGraph(limit = 300): Promise<GraphApiResponse> {
  return get<GraphApiResponse>(`/graph?limit=${limit}`)
}
