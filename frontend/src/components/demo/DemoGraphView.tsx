import { useState, useRef, useCallback, useEffect } from 'react'
import { Search, Info, X } from 'lucide-react'
import { DEMO_GRAPH, DEMO_GRAPH_INSIGHTS } from '../../data/demo-data'
import type { GraphNode } from '../../types/graph'
import '../GraphView.css'

export default function DemoGraphView() {
  const containerRef = useRef<HTMLDivElement>(null)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [showInsights, setShowInsights] = useState(false)
  const insights = DEMO_GRAPH_INSIGHTS

  // 2D 렌더링 (ForceGraph3D는 무거우므로 데모에서는 간단한 2D 시각화)
  const [ForceGraph, setForceGraph] = useState<React.ComponentType<Record<string, unknown>> | null>(null)

  useEffect(() => {
    import('react-force-graph-2d').then(mod => setForceGraph(() => mod.default))
  }, [])

  const handleNodeClick = useCallback((node: GraphNode) => {
    setSelectedNode(node)
  }, [])

  const filteredNodes = searchQuery
    ? DEMO_GRAPH.nodes.filter(n => n.label.toLowerCase().includes(searchQuery.toLowerCase()))
    : null

  return (
    <div className="graph-view">
      <div className="graph-toolbar">
        <div className="graph-search">
          <Search size={16} />
          <input
            type="text"
            placeholder="노드 검색..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
        <button className="graph-insights-toggle" onClick={() => setShowInsights(!showInsights)}>
          <Info size={16} /> 인사이트
        </button>
      </div>

      {filteredNodes && filteredNodes.length > 0 && (
        <div className="graph-search-results">
          {filteredNodes.map(n => (
            <button key={n.id} className="graph-search-item" onClick={() => { setSelectedNode(n); setSearchQuery('') }}>
              <span className={`node-type-badge ${n.group?.toLowerCase()}`}>{n.group}</span>
              {n.label}
            </button>
          ))}
        </div>
      )}

      <div className="graph-container" ref={containerRef}>
        {ForceGraph && (
          <ForceGraph
            graphData={DEMO_GRAPH}
            nodeLabel={(node: GraphNode) => node.label}
            nodeColor={(node: GraphNode) => {
              if (selectedNode && node.id === selectedNode.id) return '#6366f1'
              const colors: Record<string, string> = { Topic: '#3b82f6', Concept: '#f59e0b', Person: '#10b981' }
              return colors[node.group || ''] || '#94a3b8'
            }}
            nodeVal={(node: GraphNode) => node.val || 3}
            linkColor={() => 'rgba(148,163,184,0.3)'}
            onNodeClick={handleNodeClick}
            width={containerRef.current?.clientWidth || 800}
            height={containerRef.current?.clientHeight || 600}
            enableNodeDrag={true}
          />
        )}
      </div>

      {/* 선택된 노드 패널 */}
      {selectedNode && (
        <div className="graph-detail-panel">
          <div className="graph-detail-header">
            <h3>{selectedNode.label}</h3>
            <button onClick={() => setSelectedNode(null)}><X size={16} /></button>
          </div>
          <p className="graph-detail-type">유형: {selectedNode.group}</p>
        </div>
      )}

      {/* 인사이트 패널 */}
      {showInsights && (
        <div className="graph-insights-panel">
          <div className="graph-insights-header">
            <h3>그래프 인사이트</h3>
            <button onClick={() => setShowInsights(false)}><X size={16} /></button>
          </div>
          <div className="insights-section">
            <h4>클러스터</h4>
            {insights.clusters.map(c => (
              <div key={c.cluster_id} className="insight-cluster-card">
                <strong>{c.summary}</strong>
                <p>{c.entities.join(', ')}</p>
              </div>
            ))}
          </div>
          <div className="insights-section">
            <h4>허브 노드</h4>
            {insights.hub_nodes.map(h => (
              <div key={h.name} className="insight-hub-item">
                <strong>{h.name}</strong> — {h.degree}개 연결
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
