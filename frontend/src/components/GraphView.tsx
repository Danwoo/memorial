import { useEffect, useState, useRef, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import ForceGraph3D from 'react-force-graph-3d'
import SpriteText from 'three-spritetext'
import * as THREE from 'three'
import type { GraphNode, GraphLink, GraphData } from '../types'
import { fetchGraph } from '../api'
import './GraphView.css'

// Color palette for different node types
const NODE_COLORS: Record<string, string> = {
  Memory: '#a78bfa',
  Entity: '#34d399',
  Concept: '#60a5fa',
  Person: '#f472b6',
  Organization: '#fb923c',
  Company: '#fb923c',
  Technology: '#22d3ee',
  Platform: '#a3e635',
  Product: '#e879f9',
  Location: '#fbbf24',
  Event: '#f87171',
  Topic: '#818cf8',
  Idea: '#818cf8',
  Framework: '#22d3ee',
  Language: '#60a5fa',
  Tool: '#34d399',
  default: '#9ca3af',
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyNode = GraphNode & { x?: number; y?: number; z?: number; [k: string]: any }

export default function GraphView() {
  const navigate = useNavigate()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null)
  const nodeMaterials = useRef<Map<string, THREE.MeshLambertMaterial>>(new Map())

  const [data, setData] = useState<GraphData>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())

  // Fetch graph data
  const fetchGraphData = useCallback(async () => {
    try {
      setLoading(true)
      const json = await fetchGraph(300)
      const processedNodes: GraphNode[] = json.nodes.map(n => ({
        ...n,
        val: n.val || 1,
        color: NODE_COLORS[n.label] || NODE_COLORS['default'],
        name: n.name || (n.properties?.name as string) || (n.properties?.title as string) || n.id,
      }))
      setData({ nodes: processedNodes, links: json.links })
    } catch (err) {
      console.error('Failed to fetch graph data:', err)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchGraphData()
  }, [fetchGraphData])

  // Filtered data based on hidden types
  const filteredData = useMemo(() => {
    if (hiddenTypes.size === 0) return data
    const visibleNodes = data.nodes.filter(n => !hiddenTypes.has(n.label))
    const visibleIds = new Set(visibleNodes.map(n => n.id))
    const visibleLinks = data.links.filter(l => {
      const sid = typeof l.source === 'object' ? l.source.id : l.source
      const tid = typeof l.target === 'object' ? l.target.id : l.target
      return visibleIds.has(sid) && visibleIds.has(tid)
    })
    return { nodes: visibleNodes, links: visibleLinks }
  }, [data, hiddenTypes])

  // Unique node types for legend
  const nodeTypes = useMemo(
    () => [...new Set(data.nodes.map(n => n.label))].sort(),
    [data.nodes],
  )

  // 3D node rendering: sphere + label
  const nodeThreeObject = useCallback((node: AnyNode) => {
    const val = node.val || 1
    const size = Math.max(1.5, Math.sqrt(val) * 1.5)
    const color = node.color || NODE_COLORS['default']

    const group = new THREE.Group()

    // Sphere
    const geo = new THREE.SphereGeometry(size, 16, 12)
    const mat = new THREE.MeshLambertMaterial({
      color,
      transparent: true,
      opacity: 0.9,
    })
    const mesh = new THREE.Mesh(geo, mat)
    group.add(mesh)

    // Store material ref for hover highlighting
    nodeMaterials.current.set(node.id, mat)

    // Label sprite
    const label = (node.name || node.id).substring(0, 24)
    const sprite = new SpriteText(label)
    sprite.color = '#ffffff'
    sprite.textHeight = Math.max(1.2, size * 0.5)
    sprite.backgroundColor = 'rgba(0,0,0,0.6)'
    sprite.padding = [0.5, 1] as unknown as number
    sprite.borderRadius = 1
    sprite.position.y = -(size + 2)
    group.add(sprite)

    return group
  }, [])

  // Get link key for highlight matching
  const getLinkKey = useCallback((link: GraphLink) => {
    const sid = typeof link.source === 'object' ? link.source.id : link.source
    const tid = typeof link.target === 'object' ? link.target.id : link.target
    return `${sid}-${tid}`
  }, [])

  // Hover: highlight connected nodes/links via direct Three.js material manipulation
  const handleNodeHover = useCallback((node: AnyNode | null) => {
    if (node) {
      const connectedIds = new Set<string>([node.id])
      const connectedLinkKeys = new Set<string>()

      filteredData.links.forEach(link => {
        const sid = typeof link.source === 'object' ? link.source.id : link.source
        const tid = typeof link.target === 'object' ? link.target.id : link.target
        if (sid === node.id || tid === node.id) {
          connectedIds.add(sid)
          connectedIds.add(tid)
          connectedLinkKeys.add(`${sid}-${tid}`)
        }
      })

      // Dim non-connected nodes
      nodeMaterials.current.forEach((mat, id) => {
        mat.opacity = connectedIds.has(id) ? 1.0 : 0.1
      })

      setHighlightLinks(connectedLinkKeys)
    } else {
      // Restore all nodes
      nodeMaterials.current.forEach(mat => {
        mat.opacity = 0.9
      })
      setHighlightLinks(new Set())
    }
  }, [filteredData.links])

  // Click: fly camera to node
  const handleNodeClick = useCallback((node: AnyNode) => {
    setSelectedNode(node)
    const distance = 60
    const distRatio = 1 + distance / Math.hypot(node.x || 1, node.y || 1, node.z || 1)
    fgRef.current?.cameraPosition(
      { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
      { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
      1000,
    )
  }, [])

  // Background click: deselect
  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null)
    setHighlightLinks(new Set())
    nodeMaterials.current.forEach(mat => {
      mat.opacity = 0.9
    })
  }, [])

  // Search: find node and fly to it
  const handleSearch = useCallback(
    (query: string) => {
      if (!query.trim()) return
      const q = query.toLowerCase()
      const match = filteredData.nodes.find(n =>
        (n.name || n.id).toLowerCase().includes(q),
      )
      if (match && fgRef.current) {
        const node = match as AnyNode
        setSelectedNode(match)
        const distance = 60
        const distRatio = 1 + distance / Math.hypot(node.x || 1, node.y || 1, node.z || 1)
        fgRef.current.cameraPosition(
          { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
          { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
          1000,
        )
      }
    },
    [filteredData.nodes],
  )

  // Toggle type visibility
  const toggleType = useCallback((type: string) => {
    setHiddenTypes(prev => {
      const next = new Set(prev)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }, [])

  // Start chat with topic
  const handleStartChat = useCallback(
    (node: GraphNode) => {
      navigate('/chat', { state: { topic: node.name || node.id, mode: 'insight' } })
    },
    [navigate],
  )

  // Connections for selected node
  const selectedConnections = useMemo(() => {
    if (!selectedNode) return []
    return filteredData.links
      .filter(l => {
        const sid = typeof l.source === 'object' ? l.source.id : l.source
        const tid = typeof l.target === 'object' ? l.target.id : l.target
        return sid === selectedNode.id || tid === selectedNode.id
      })
      .map(l => {
        const sid = typeof l.source === 'object' ? l.source.id : l.source
        const tid = typeof l.target === 'object' ? l.target.id : l.target
        const otherId = sid === selectedNode.id ? tid : sid
        const other = filteredData.nodes.find(n => n.id === otherId)
        return {
          id: otherId,
          name: other?.name || otherId,
          label: other?.label || '',
          type: l.type,
          color: other?.color || NODE_COLORS['default'],
        }
      })
  }, [selectedNode, filteredData])

  const isEmptyGraph = !loading && data.nodes.length === 0

  return (
    <div className="graph-view-container">
      {/* Search bar */}
      {!loading && !isEmptyGraph && (
        <div className="graph-search">
          <div className="search-input-wrapper">
            <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="text"
              placeholder="Search nodes..."
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && handleSearch(searchQuery)}
            />
          </div>
        </div>
      )}

      {/* Stats */}
      {!loading && !isEmptyGraph && (
        <div className="graph-stats">
          {filteredData.nodes.length} nodes &middot; {filteredData.links.length} connections
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="graph-loader">
          <div className="loader-spinner" />
          <p>Loading Knowledge Graph...</p>
        </div>
      )}

      {/* Empty state */}
      {isEmptyGraph && (
        <div className="graph-empty">
          <div className="empty-icon">
            <svg viewBox="0 0 120 120" fill="none" width="80" height="80">
              <circle cx="30" cy="40" r="8" fill="#a78bfa" opacity="0.6" />
              <circle cx="90" cy="35" r="6" fill="#34d399" opacity="0.6" />
              <circle cx="60" cy="80" r="10" fill="#60a5fa" opacity="0.6" />
              <circle cx="45" cy="25" r="5" fill="#f472b6" opacity="0.6" />
              <circle cx="80" cy="70" r="7" fill="#fb923c" opacity="0.6" />
              <line x1="30" y1="40" x2="60" y2="80" stroke="#555" strokeWidth="1" opacity="0.4" />
              <line x1="90" y1="35" x2="60" y2="80" stroke="#555" strokeWidth="1" opacity="0.4" />
              <line x1="30" y1="40" x2="45" y2="25" stroke="#555" strokeWidth="1" opacity="0.4" />
              <line x1="90" y1="35" x2="80" y2="70" stroke="#555" strokeWidth="1" opacity="0.4" />
            </svg>
          </div>
          <h3>Knowledge Graph is empty</h3>
          <p>
            Add memories to build your knowledge graph.<br />
            Entities and connections will be automatically extracted.
          </p>
          <button onClick={() => navigate('/memories')} className="add-memory-btn">
            + Add Memory
          </button>
        </div>
      )}

      {/* 3D Graph */}
      {!loading && !isEmptyGraph && (
        <ForceGraph3D
          ref={fgRef}
          graphData={filteredData}
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={false}
          linkColor={(link: GraphLink) =>
            highlightLinks.has(getLinkKey(link))
              ? 'rgba(255,255,255,0.8)'
              : 'rgba(255,255,255,0.12)'
          }
          linkWidth={(link: GraphLink) => (highlightLinks.has(getLinkKey(link)) ? 1.5 : 0.3)}
          linkDirectionalArrowLength={3}
          linkDirectionalArrowRelPos={1}
          linkDirectionalParticles={(link: GraphLink) =>
            highlightLinks.has(getLinkKey(link)) ? 3 : 0
          }
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleSpeed={0.006}
          backgroundColor="#0a0a0f"
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          onBackgroundClick={handleBackgroundClick}
          cooldownTicks={100}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 100)}
        />
      )}

      {/* Legend */}
      {!loading && nodeTypes.length > 0 && (
        <div className="graph-legend">
          <h4>Node Types</h4>
          <div className="legend-items">
            {nodeTypes.map(type => (
              <div
                key={type}
                className={`legend-item ${hiddenTypes.has(type) ? 'legend-item-hidden' : ''}`}
                onClick={() => toggleType(type)}
              >
                <span
                  className="legend-dot"
                  style={{
                    backgroundColor: hiddenTypes.has(type)
                      ? '#444'
                      : NODE_COLORS[type] || NODE_COLORS['default'],
                  }}
                />
                <span className="legend-label">{type}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Selected Node Info Panel */}
      {selectedNode && (
        <div className="node-info-panel">
          <div className="node-info-header">
            <span
              className="node-type-badge"
              style={{ backgroundColor: selectedNode.color }}
            >
              {selectedNode.label}
            </span>
            <button className="close-btn" onClick={() => setSelectedNode(null)}>
              &times;
            </button>
          </div>
          <h3>{selectedNode.name}</h3>

          {selectedNode.properties?.summary && (
            <p className="node-summary">{selectedNode.properties.summary as string}</p>
          )}

          {selectedNode.properties?.tags && (
            <div className="node-tags">
              {(selectedNode.properties.tags as string[]).map((tag: string, i: number) => (
                <span key={i} className="node-tag">
                  #{tag}
                </span>
              ))}
            </div>
          )}

          {selectedConnections.length > 0 && (
            <div className="node-connections">
              <h4>Connections ({selectedConnections.length})</h4>
              <ul>
                {selectedConnections.slice(0, 10).map((conn, i) => (
                  <li key={i}>
                    <span className="conn-dot" style={{ backgroundColor: conn.color }} />
                    <span className="conn-type">{conn.type}</span>
                    <span className="conn-name">{conn.name}</span>
                  </li>
                ))}
                {selectedConnections.length > 10 && (
                  <li className="conn-more">+{selectedConnections.length - 10} more</li>
                )}
              </ul>
            </div>
          )}

          <button
            className="chat-with-topic-btn"
            onClick={() => handleStartChat(selectedNode)}
          >
            이 주제로 대화하기
          </button>
        </div>
      )}

      {/* Controls hint */}
      {!loading && !isEmptyGraph && (
        <div className="graph-controls">
          <span>Drag: Rotate</span>
          <span>Scroll: Zoom</span>
          <span>Click: Focus</span>
          <span>Right-drag: Pan</span>
        </div>
      )}
    </div>
  )
}
