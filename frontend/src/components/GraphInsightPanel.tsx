import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  TrendingUp, TrendingDown, Minus,
  Link2, Zap, CircleDot, MessageSquare, BookOpen,
} from 'lucide-react'
import type { GraphInsights, ClusterInfo, SearchResult } from '../types'
import { searchMemories, createGraphRelation } from '../api'
import { useToast } from '../contexts/ToastContext'
import './GraphInsightPanel.css'

// 클러스터 색상 팔레트
const CLUSTER_COLORS = [
  '#6366f1', '#f59e0b', '#10b981', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16',
]

interface Props {
  insights: GraphInsights | null
  loading: boolean
  onClusterSelect: (cluster: ClusterInfo) => void
  onIsolatedNodeClick: (name: string) => void
  onHubNodeClick: (name: string) => void
  onConnectionCreated: () => void
}

export default function GraphInsightPanel({
  insights,
  loading,
  onClusterSelect,
  onIsolatedNodeClick,
  onHubNodeClick,
  onConnectionCreated,
}: Props) {
  const navigate = useNavigate()
  const toast = useToast()
  const [connectingNode, setConnectingNode] = useState<string | null>(null)
  const [searchResults, setSearchResults] = useState<SearchResult[]>([])
  const [searchLoading, setSearchLoading] = useState(false)

  const handleConnectClick = async (nodeName: string) => {
    if (connectingNode === nodeName) {
      setConnectingNode(null)
      setSearchResults([])
      return
    }
    setConnectingNode(nodeName)
    setSearchLoading(true)
    try {
      const res = await searchMemories({ q: nodeName, limit: 5 })
      setSearchResults(res.results ?? [])
    } catch {
      setSearchResults([])
    } finally {
      setSearchLoading(false)
    }
  }

  const handleCreateConnection = async (targetName: string) => {
    if (!connectingNode) return
    try {
      await createGraphRelation(connectingNode, targetName)
      toast.success(`${connectingNode} → ${targetName} 연결 생성됨`)
      setConnectingNode(null)
      setSearchResults([])
      onConnectionCreated()
    } catch {
      toast.error('연결 생성에 실패했습니다')
    }
  }

  if (loading) {
    return (
      <div className="insight-panel">
        <h3 className="insight-panel-title">인사이트</h3>
        <div className="insight-panel-loading">
          <div className="loading-spinner small" />
          <span>분석 중...</span>
        </div>
      </div>
    )
  }

  if (!insights) return null

  const hasContent =
    insights.clusters.length > 0 ||
    insights.trends.length > 0 ||
    insights.isolated_nodes.length > 0 ||
    insights.hub_nodes.length > 0

  if (!hasContent) {
    return (
      <div className="insight-panel">
        <h3 className="insight-panel-title">인사이트</h3>
        <p className="insight-panel-empty">아직 분석할 데이터가 부족합니다. 더 많은 기억을 추가해보세요.</p>
      </div>
    )
  }

  return (
    <div className="insight-panel">
      <h3 className="insight-panel-title">인사이트</h3>

      {/* 클러스터 */}
      {insights.clusters.length > 0 && (
        <div className="insight-section">
          <h4 className="insight-section-title">
            <CircleDot size={14} />
            주제 클러스터
          </h4>
          <div className="insight-cluster-list">
            {insights.clusters.map((cluster, i) => (
              <div key={cluster.cluster_id} className="insight-cluster-card-wrapper">
                <button
                  className="insight-cluster-card"
                  onClick={() => onClusterSelect(cluster)}
                  style={{ borderLeftColor: CLUSTER_COLORS[i % CLUSTER_COLORS.length] }}
                >
                  <span className="cluster-summary">
                    {cluster.summary || `클러스터 ${cluster.cluster_id + 1}`}
                  </span>
                  <span className="cluster-meta">{cluster.size}개 엔티티</span>
                </button>
                <button
                  className="cluster-chat-btn"
                  onClick={() => navigate('/chat', { state: { topic: cluster.summary || cluster.entities[0] } })}
                  title="이 주제에 대해 대화하기"
                >
                  <MessageSquare size={12} />
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 트렌드 */}
      {insights.trends.length > 0 && (
        <div className="insight-section">
          <h4 className="insight-section-title">
            <TrendingUp size={14} />
            태그 트렌드
          </h4>
          <div className="insight-trend-list">
            {insights.trends.map(trend => (
              <div key={trend.tag} className="insight-trend-item">
                <span className="trend-tag">#{trend.tag}</span>
                <div className="trend-bars">
                  {trend.counts.map((c, i) => (
                    <div
                      key={i}
                      className="trend-bar"
                      style={{ height: `${Math.max(4, (c / Math.max(...trend.counts, 1)) * 24)}px` }}
                    />
                  ))}
                </div>
                <span className="trend-direction">
                  {trend.direction === 'up' && <TrendingUp size={12} className="trend-up" />}
                  {trend.direction === 'down' && <TrendingDown size={12} className="trend-down" />}
                  {trend.direction === 'stable' && <Minus size={12} className="trend-stable" />}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 고립 노드 */}
      {insights.isolated_nodes.length > 0 && (
        <div className="insight-section">
          <div className="insight-section-header">
            <h4 className="insight-section-title">
              <Link2 size={14} />
              고립 엔티티
            </h4>
            <button className="section-link" onClick={() => navigate('/memories')}>
              <BookOpen size={12} />
              기억 뷰에서 보기
            </button>
          </div>
          <div className="insight-isolated-list">
            {insights.isolated_nodes.slice(0, 8).map(node => (
              <div key={node.name} className="insight-isolated-item">
                <button
                  className="isolated-name"
                  onClick={() => onIsolatedNodeClick(node.name)}
                >
                  {node.name}
                </button>
                <button
                  className={`isolated-connect-btn ${connectingNode === node.name ? 'active' : ''}`}
                  onClick={() => handleConnectClick(node.name)}
                >
                  연결 만들기
                </button>
                {connectingNode === node.name && (
                  <div className="connect-dropdown">
                    {searchLoading && <span className="connect-loading">검색 중...</span>}
                    {!searchLoading && searchResults.length === 0 && (
                      <span className="connect-empty">유사 메모리 없음</span>
                    )}
                    {!searchLoading && searchResults.map(r => (
                      <button
                        key={r.id}
                        className="connect-option"
                        onClick={() => handleCreateConnection(r.title || r.content?.substring(0, 30) || r.id)}
                      >
                        {r.title || r.content?.substring(0, 40) || '메모리'}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 허브 노드 */}
      {insights.hub_nodes.length > 0 && (
        <div className="insight-section">
          <h4 className="insight-section-title">
            <Zap size={14} />
            핵심 허브
          </h4>
          <div className="insight-hub-list">
            {insights.hub_nodes.map(hub => (
              <button
                key={hub.name}
                className="insight-hub-item"
                onClick={() => onHubNodeClick(hub.name)}
              >
                <span className="hub-name">{hub.name}</span>
                <span className="hub-degree">{hub.degree}개 연결</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export { CLUSTER_COLORS }
