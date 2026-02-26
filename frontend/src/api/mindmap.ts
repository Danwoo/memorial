import { get, post } from './client'
import type { MindmapInsights } from '../types'
import { isDemoMode } from '../contexts/DemoContext'
import { DEMO_MINDMAP, DEMO_MINDMAP_INSIGHTS } from '../data/demo-data'

interface MindmapApiResponse {
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

// 마인드맵 노드 및 링크 데이터 조회
export function fetchMindmap(limit = 300): Promise<MindmapApiResponse> {
  if (isDemoMode()) return Promise.resolve(DEMO_MINDMAP as unknown as MindmapApiResponse)
  return get<MindmapApiResponse>(`/mindmap?limit=${limit}`)
}

// 마인드맵 인사이트 분석 결과 조회
export function fetchMindmapInsights(): Promise<MindmapInsights> {
  if (isDemoMode()) return Promise.resolve(DEMO_MINDMAP_INSIGHTS)
  return get<MindmapInsights>('/mindmap/insights')
}

// 수동 관계 생성
export function createMindmapRelation(source: string, target: string, relType = 'RELATED_TO'): Promise<{ ok: boolean; message: string }> {
  if (isDemoMode()) return Promise.resolve({ ok: true, message: '데모 모드' })
  return post('/mindmap/relations', { source, target, rel_type: relType })
}

// Ego 마인드맵 조회 (특정 노드 중심 N-hop)
export function fetchEgoMindmap(nodeName: string, depth = 1): Promise<MindmapApiResponse & { center_node?: string }> {
  if (isDemoMode()) return Promise.resolve({ ...DEMO_MINDMAP as unknown as MindmapApiResponse, center_node: nodeName })
  return get<MindmapApiResponse & { center_node?: string }>(`/mindmap/ego?node_name=${encodeURIComponent(nodeName)}&depth=${depth}`)
}

// Ego 마인드맵 기본 조회 (가장 연결이 많은 노드 중심)
export function fetchEgoDefault(): Promise<MindmapApiResponse & { center_node?: string | null }> {
  if (isDemoMode()) return Promise.resolve({ ...DEMO_MINDMAP as unknown as MindmapApiResponse, center_node: null })
  return get<MindmapApiResponse & { center_node?: string | null }>('/mindmap/ego/default')
}
