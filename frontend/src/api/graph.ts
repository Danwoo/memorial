import { get, post } from './client'
import type { GraphInsights } from '../types'
import { isDemoMode } from '../contexts/DemoContext'
import { DEMO_GRAPH, DEMO_GRAPH_INSIGHTS } from '../data/demo-data'

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
  if (isDemoMode()) return Promise.resolve(DEMO_GRAPH as unknown as GraphApiResponse)
  return get<GraphApiResponse>(`/graph?limit=${limit}`)
}

// 그래프 인사이트 분석 결과 조회
export function fetchGraphInsights(): Promise<GraphInsights> {
  if (isDemoMode()) return Promise.resolve(DEMO_GRAPH_INSIGHTS)
  return get<GraphInsights>('/graph/insights')
}

// 수동 관계 생성
export function createGraphRelation(source: string, target: string, relType = 'RELATED_TO'): Promise<{ ok: boolean; message: string }> {
  if (isDemoMode()) return Promise.resolve({ ok: true, message: '데모 모드' })
  return post('/graph/relations', { source, target, rel_type: relType })
}

// Ego 그래프 조회 (특정 노드 중심 N-hop)
export function fetchEgoGraph(nodeName: string, depth = 1): Promise<GraphApiResponse & { center_node?: string }> {
  if (isDemoMode()) return Promise.resolve({ ...DEMO_GRAPH as unknown as GraphApiResponse, center_node: nodeName })
  return get<GraphApiResponse & { center_node?: string }>(`/graph/ego?node_name=${encodeURIComponent(nodeName)}&depth=${depth}`)
}

// Ego 그래프 기본 조회 (가장 연결이 많은 노드 중심)
export function fetchEgoDefault(): Promise<GraphApiResponse & { center_node?: string | null }> {
  if (isDemoMode()) return Promise.resolve({ ...DEMO_GRAPH as unknown as GraphApiResponse, center_node: null })
  return get<GraphApiResponse & { center_node?: string | null }>('/graph/ego/default')
}
