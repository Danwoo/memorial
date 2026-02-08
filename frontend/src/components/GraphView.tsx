import { useEffect, useState, useRef, useCallback } from 'react'
import ForceGraph2D from 'react-force-graph-2d'
import type { GraphNode, GraphLink, GraphData } from '../types'
import './GraphView.css'

// Color palette for different node types
const NODE_COLORS: Record<string, string> = {
  'Memory': '#a78bfa',      // Purple
  'Entity': '#34d399',      // Emerald
  'Concept': '#60a5fa',     // Blue
  'Person': '#f472b6',      // Pink
  'Project': '#fbbf24',     // Amber
  'Topic': '#818cf8',       // Indigo
  'Resource': '#2dd4bf',    // Teal
  'default': '#9ca3af'      // Gray
}

const NODE_SIZES: Record<string, number> = {
  'Memory': 12,
  'Entity': 8,
  'Concept': 10,
  'Person': 10,
  'Project': 14,
  'Topic': 9,
  'Resource': 11,
  'default': 6
}

export default function GraphView() {
  const [data, setData] = useState<GraphData>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [highlightNodes, setHighlightNodes] = useState<Set<string>>(new Set())
  const [highlightLinks, setHighlightLinks] = useState<Set<GraphLink>>(new Set())
  const fgRef = useRef<any>()

  useEffect(() => {
    fetchGraphData()
  }, [])

  const fetchGraphData = async () => {
    try {
      setLoading(true)
      const res = await fetch('/api/v1/graph?limit=200')

      if (!res.ok) {
        throw new Error(`API responded with status ${res.status}`)
      }

      const json = await res.json()

      // Process nodes with proper styling
      const processedNodes = json.nodes.map((n: any) => ({
        ...n,
        val: NODE_SIZES[n.label] || NODE_SIZES['default'],
        color: NODE_COLORS[n.label] || NODE_COLORS['default'],
        name: n.properties?.title || n.properties?.name || n.name || n.id
      }))

      setData({
        nodes: processedNodes,
        links: json.links
      })
    } catch (err) {
      console.error("Failed to fetch graph data, falling back to mock:", err)
      // Fallback: fetch with mock=true only when real API fails
      try {
        const mockRes = await fetch('/api/v1/graph?limit=200&mock=true')
        const mockJson = await mockRes.json()
        const processedNodes = mockJson.nodes.map((n: any) => ({
          ...n,
          val: NODE_SIZES[n.label] || NODE_SIZES['default'],
          color: NODE_COLORS[n.label] || NODE_COLORS['default'],
          name: n.properties?.title || n.properties?.name || n.name || n.id
        }))
        setData({ nodes: processedNodes, links: mockJson.links })
      } catch (mockErr) {
        console.error("Mock fallback also failed:", mockErr)
      }
    } finally {
      setLoading(false)
    }
  }

  // Custom node canvas rendering for better labels
  const paintNode = useCallback((node: any, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const label = node.name || node.id
    const fontSize = Math.max(12 / globalScale, 3)
    const nodeSize = node.val || 6
    const isHighlighted = highlightNodes.has(node.id)
    const isSelected = selectedNode?.id === node.id
    
    // Draw node circle
    ctx.beginPath()
    ctx.arc(node.x, node.y, nodeSize, 0, 2 * Math.PI, false)
    ctx.fillStyle = node.color
    if (isHighlighted || isSelected) {
      ctx.shadowColor = node.color
      ctx.shadowBlur = 15
    }
    ctx.fill()
    ctx.shadowBlur = 0
    
    // Draw border for selected/highlighted nodes
    if (isSelected) {
      ctx.strokeStyle = '#fff'
      ctx.lineWidth = 2 / globalScale
      ctx.stroke()
    } else if (isHighlighted) {
      ctx.strokeStyle = 'rgba(255,255,255,0.5)'
      ctx.lineWidth = 1 / globalScale
      ctx.stroke()
    }
    
    // Draw label if zoomed in enough
    if (globalScale > 0.8) {
      ctx.font = `${fontSize}px Inter, sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'middle'
      
      // Text background
      const textWidth = ctx.measureText(label.substring(0, 20)).width
      ctx.fillStyle = 'rgba(0, 0, 0, 0.7)'
      ctx.fillRect(
        node.x - textWidth / 2 - 2,
        node.y + nodeSize + 3,
        textWidth + 4,
        fontSize + 2
      )
      
      // Text
      ctx.fillStyle = '#fff'
      ctx.fillText(label.substring(0, 20), node.x, node.y + nodeSize + 3 + fontSize / 2)
    }
  }, [highlightNodes, selectedNode])

  // Handle node hover for highlighting connections
  const handleNodeHover = useCallback((node: GraphNode | null) => {
    setHighlightNodes(new Set())
    setHighlightLinks(new Set())
    
    if (node) {
      const connectedNodeIds = new Set<string>()
      const connectedLinks = new Set<GraphLink>()
      
      data.links.forEach(link => {
        const sourceId = typeof link.source === 'object' ? link.source.id : link.source
        const targetId = typeof link.target === 'object' ? link.target.id : link.target
        
        if (sourceId === node.id || targetId === node.id) {
          connectedNodeIds.add(sourceId)
          connectedNodeIds.add(targetId)
          connectedLinks.add(link)
        }
      })
      
      setHighlightNodes(connectedNodeIds)
      setHighlightLinks(connectedLinks)
    }
  }, [data.links])

  const handleNodeClick = useCallback((node: any) => {
    setSelectedNode(node)
    if (node.url) {
      window.open(node.url, '_blank')
    }
    fgRef.current?.centerAt(node.x, node.y, 500)
    fgRef.current?.zoom(3, 500)
  }, [])

  // Get unique node types for legend
  const nodeTypes = [...new Set(data.nodes.map(n => n.label))]

  return (
    <div className="graph-view-container">
      <div className="graph-header">
        <h2>🕸️ Knowledge Graph</h2>
        <span className="node-count">{data.nodes.length} nodes · {data.links.length} connections</span>
      </div>

      {loading && (
        <div className="graph-loader">
          <div className="loader-spinner"></div>
          <p>Loading Knowledge Graph...</p>
        </div>
      )}
      
      {!loading && (
        <ForceGraph2D
          ref={fgRef}
          graphData={data}
          nodeCanvasObject={paintNode}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            ctx.fillStyle = color
            ctx.beginPath()
            ctx.arc(node.x, node.y, node.val || 6, 0, 2 * Math.PI)
            ctx.fill()
          }}
          linkColor={(link: any) => 
            highlightLinks.has(link) ? 'rgba(255,255,255,0.8)' : 'rgba(255,255,255,0.15)'
          }
          linkWidth={(link: any) => highlightLinks.has(link) ? 2 : 0.5}
          linkDirectionalParticles={(link: any) => highlightLinks.has(link) ? 4 : 0}
          linkDirectionalParticleWidth={2}
          backgroundColor="#0f0f0f"
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          cooldownTicks={100}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 50)}
          enableNodeDrag={true}
          enableZoomInteraction={true}
          enablePanInteraction={true}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
        />
      )}
      
      {/* Legend */}
      <div className="graph-legend">
        <h4>Node Types</h4>
        <div className="legend-items">
          {nodeTypes.map(type => (
            <div key={type} className="legend-item">
              <span 
                className="legend-dot" 
                style={{ backgroundColor: NODE_COLORS[type] || NODE_COLORS['default'] }}
              />
              <span className="legend-label">{type}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Selected Node Info */}
      {selectedNode && (
        <div className="node-info-panel">
          <div className="node-info-header">
            <span 
              className="node-type-badge"
              style={{ backgroundColor: selectedNode.color }}
            >
              {selectedNode.label}
            </span>
            <button className="close-btn" onClick={() => setSelectedNode(null)}>×</button>
          </div>
          <h3>{selectedNode.name}</h3>
          {selectedNode.properties?.summary && (
            <p className="node-summary">{selectedNode.properties.summary}</p>
          )}
          {selectedNode.properties?.tags && (
            <div className="node-tags">
              {selectedNode.properties.tags.map((tag: string, i: number) => (
                <span key={i} className="node-tag">#{tag}</span>
              ))}
            </div>
          )}
        </div>
      )}
      
      <div className="graph-controls">
        <span>🖱️ Scroll: Zoom</span>
        <span>✋ Drag: Pan</span>
        <span>👆 Click: Focus</span>
        <span>🔍 Hover: Highlight</span>
      </div>
    </div>
  )
}

