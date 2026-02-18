import { get, post } from './client'
import type { GraphInsights } from '../types'

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

// 그래프 인사이트 분석 결과 조회
export function fetchGraphInsights(): Promise<GraphInsights> {
  return get<GraphInsights>('/graph/insights')
}

// 수동 관계 생성
export function createGraphRelation(source: string, target: string, relType = 'RELATED_TO'): Promise<{ ok: boolean; message: string }> {
  return post('/graph/relations', { source, target, rel_type: relType })
}
