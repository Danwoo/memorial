import { useEffect, useState, useRef, useCallback, useMemo } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'
import { Lightbulb, Maximize, ZoomIn, ZoomOut } from 'lucide-react'
import type { GraphNode, GraphLink, GraphData, SearchResult, GraphInsights, ClusterInfo } from '../types'
import { useTheme } from '../contexts/ThemeContext'
import { useToast } from '../contexts/ToastContext'
import { fetchGraph, fetchGraphInsights, searchMemories } from '../api'
import MemoryDetailModal from './MemoryDetailModal'
import GraphInsightPanel, { CLUSTER_COLORS } from './GraphInsightPanel'
import NodeInfoPanel from './graph/NodeInfoPanel'
import GraphLegend from './graph/GraphLegend'
import { NODE_COLORS, NODE_TYPE_KO } from './graph/graphConstants'
import { smartSearch, type SearchCandidate } from '../utils/searchUtils'
import './GraphView.css'

type AnyNode = GraphNode & { x?: number; y?: number; vx?: number; vy?: number; fx?: number; fy?: number }

const CAMERA_STORAGE_KEY = 'memoir-graph-camera'
const ONBOARDING_KEY = 'memoir-graph-visited'

export default function GraphView() {
  const navigate = useNavigate()
  const location = useLocation()
  const { resolvedTheme } = useTheme()
  const toast = useToast()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null)
  const cameraRestoredRef = useRef(false)

  const [data, setData] = useState<GraphData>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set())
  const [highlightNodes, setHighlightNodes] = useState<Set<string> | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())

  // 관련 메모리 조회
  const [relatedMemories, setRelatedMemories] = useState<SearchResult[]>([])
  const [isLoadingMemories, setIsLoadingMemories] = useState(false)
  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null)

  // 검색 결과 하이라이트
  const [searchMatches, setSearchMatches] = useState<GraphNode[]>([])
  const [searchMatchIdx, setSearchMatchIdx] = useState(0)
  const [searchCandidates, setSearchCandidates] = useState<SearchCandidate[]>([])
  const [showSearchDropdown, setShowSearchDropdown] = useState(false)

  // 온보딩 오버레이
  const [showOnboarding, setShowOnboarding] = useState(() => !localStorage.getItem(ONBOARDING_KEY))

  // 인사이트 패널
  const [insights, setInsights] = useState<GraphInsights | null>(null)
  const [insightsLoading, setInsightsLoading] = useState(false)
  const [showInsights, setShowInsights] = useState(false)
  const [clusterColorMode, setClusterColorMode] = useState(false)

  const bgColor = resolvedTheme === 'dark' ? '#1a1a1a' : '#ffffff'
  const textColor = resolvedTheme === 'dark' ? '#f0f0f0' : '#1a1a1a'
  const labelBg = resolvedTheme === 'dark' ? 'rgba(0,0,0,0.75)' : 'rgba(255,255,255,0.92)'

  // 그래프 데이터 조회 및 노드 가공
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
      console.error('그래프 데이터 로딩 실패:', err)
      toast.error('지식 그래프를 불러오지 못했습니다')
    } finally {
      setLoading(false)
    }
  }, [toast])

  const loadInsights = useCallback(async () => {
    setInsightsLoading(true)
    try {
      const data = await fetchGraphInsights()
      setInsights(data)
    } catch {
      setInsights(null)
    } finally {
      setInsightsLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchGraphData()
  }, [fetchGraphData])

  // 다른 뷰에서 focusNodeId로 진입 시 해당 노드 포커스
  useEffect(() => {
    const state = location.state as { focusNodeId?: string } | null
    if (state?.focusNodeId && data.nodes.length > 0) {
      const target = data.nodes.find(n => n.id === state.focusNodeId) as AnyNode | undefined
      if (target && fgRef.current) {
        setSelectedNode(target)
        setTimeout(() => {
          fgRef.current?.centerAt(target.x || 0, target.y || 0, 600)
          fgRef.current?.zoom(4, 600)
        }, 500)
      }
      window.history.replaceState({}, '')
    }
  }, [location.state, data.nodes])

  // 카메라 상태 sessionStorage 저장 (디바운스 500ms)
  const cameraSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const handleZoom = useCallback(({ k, x, y }: { k: number; x: number; y: number }) => {
    if (cameraSaveTimerRef.current) clearTimeout(cameraSaveTimerRef.current)
    cameraSaveTimerRef.current = setTimeout(() => {
      sessionStorage.setItem(CAMERA_STORAGE_KEY, JSON.stringify({ k, x, y }))
    }, 500)
  }, [])

  // 줌 컨트롤 핸들러
  const handleZoomToFit = useCallback(() => {
    fgRef.current?.zoomToFit(400, 40)
  }, [])

  const handleZoomIn = useCallback(() => {
    if (!fgRef.current) return
    const currentZoom = fgRef.current.zoom()
    fgRef.current.zoom(currentZoom * 1.5, 300)
  }, [])

  const handleZoomOut = useCallback(() => {
    if (!fgRef.current) return
    const currentZoom = fgRef.current.zoom()
    fgRef.current.zoom(currentZoom / 1.5, 300)
  }, [])

  // 온보딩 닫기
  const dismissOnboarding = useCallback(() => {
    setShowOnboarding(false)
    localStorage.setItem(ONBOARDING_KEY, '1')
  }, [])

  // 선택 노드 변경 시 관련 메모리 조회
  useEffect(() => {
    if (!selectedNode) {
      setRelatedMemories([])
      return
    }
    let cancelled = false
    const fetchRelated = async () => {
      setIsLoadingMemories(true)
      try {
        const res = await searchMemories({ q: selectedNode.name || selectedNode.id, limit: 5 })
        if (!cancelled) setRelatedMemories(res.results ?? [])
      } catch {
        if (!cancelled) setRelatedMemories([])
      } finally {
        if (!cancelled) setIsLoadingMemories(false)
      }
    }
    fetchRelated()
    return () => { cancelled = true }
  }, [selectedNode])

  // 숨겨진 타입을 제외한 필터링 데이터
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

  // 범례용 고유 노드 타입 목록
  const nodeTypes = useMemo(
    () => [...new Set(data.nodes.map(n => n.label))].sort(),
    [data.nodes],
  )

  // 클러스터 색상 모드에서 노드 색상 결정
  const getNodeColor = useCallback(
    (node: GraphNode): string => {
      if (!clusterColorMode || !insights?.clusters) {
        return NODE_COLORS[node.label] || NODE_COLORS['default']
      }
      const idx = insights.clusters.findIndex(c =>
        c.entities.includes(node.name || node.id),
      )
      if (idx >= 0) return CLUSTER_COLORS[idx % CLUSTER_COLORS.length]
      return '#555555'
    },
    [clusterColorMode, insights],
  )

  // 2D 노드 Canvas 렌더링
  const nodeCanvasObject = useCallback((node: AnyNode, ctx: CanvasRenderingContext2D, globalScale: number) => {
    const val = node.val || 1
    const size = Math.max(3, Math.sqrt(val) * 2.5)
    const color = clusterColorMode ? getNodeColor(node) : (node.color || NODE_COLORS['default'])
    const label = (node.name || node.id).substring(0, 30)

    // 하이라이트 상태에 따른 투명도
    const isHighlighted = !highlightNodes || highlightNodes.has(node.id)
    const alpha = isHighlighted ? 0.92 : 0.12

    // 원 그리기
    ctx.beginPath()
    ctx.arc(node.x || 0, node.y || 0, size, 0, 2 * Math.PI)
    ctx.fillStyle = color
    ctx.globalAlpha = alpha
    ctx.fill()
    ctx.globalAlpha = 1

    // 라벨 (줌 레벨에 따라 보이기)
    if (globalScale > 0.6 && isHighlighted) {
      const fontSize = Math.max(3.5, size * 0.7) / globalScale
      ctx.font = `500 ${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`
      ctx.textAlign = 'center'
      ctx.textBaseline = 'top'

      const textWidth = ctx.measureText(label).width
      const padding = 2 / globalScale
      const labelY = (node.y || 0) + size + 2 / globalScale

      // 라벨 배경
      ctx.fillStyle = labelBg
      ctx.globalAlpha = isHighlighted ? 0.85 : 0.3
      ctx.fillRect(
        (node.x || 0) - textWidth / 2 - padding,
        labelY - padding,
        textWidth + padding * 2,
        fontSize + padding * 2,
      )
      ctx.globalAlpha = 1

      // 라벨 텍스트
      ctx.fillStyle = textColor
      ctx.globalAlpha = isHighlighted ? 1 : 0.2
      ctx.fillText(label, node.x || 0, labelY)
      ctx.globalAlpha = 1
    }
  }, [clusterColorMode, getNodeColor, highlightNodes, labelBg, textColor])

  // 하이라이트 매칭용 링크 키 생성
  const getLinkKey = useCallback((link: GraphLink) => {
    const sid = typeof link.source === 'object' ? link.source.id : link.source
    const tid = typeof link.target === 'object' ? link.target.id : link.target
    return `${sid}-${tid}`
  }, [])

  // 호버 시 연결된 노드/링크 하이라이트
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

      setHighlightNodes(connectedIds)
      setHighlightLinks(connectedLinkKeys)
    } else {
      setHighlightNodes(null)
      setHighlightLinks(new Set())
    }
  }, [filteredData.links])

  // 더블클릭 감지를 위한 ref
  const lastClickRef = useRef<{ id: string; time: number }>({ id: '', time: 0 })

  // 클릭 시 해당 노드로 이동, 더블클릭 시 메모리 상세 모달
  const handleNodeClick = useCallback((node: AnyNode) => {
    const now = Date.now()
    const last = lastClickRef.current
    if (last.id === node.id && now - last.time < 400) {
      // 더블클릭: 관련 메모리에서 첫 번째 결과를 모달로 열기
      searchMemories({ q: node.name || node.id, limit: 1 }).then(res => {
        const first = res.results?.[0]
        if (first) setSelectedMemoryId(first.id)
      }).catch(() => {})
      lastClickRef.current = { id: '', time: 0 }
      return
    }
    lastClickRef.current = { id: node.id, time: now }

    setSelectedNode(node)
    if (showInsights) setShowInsights(false)
    // 2D 카메라 이동
    if (fgRef.current) {
      fgRef.current.centerAt(node.x || 0, node.y || 0, 600)
      fgRef.current.zoom(4, 600)
    }
  }, [showInsights])

  // 배경 클릭 시 선택 해제
  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null)
    setHighlightLinks(new Set())
    setHighlightNodes(null)
    setSearchMatches([])
  }, [])

  // 스마트 검색 디바운스 타이머
  const searchTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  // 스마트 검색 onChange 핸들러
  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const q = e.target.value
    setSearchQuery(q)

    if (searchTimerRef.current) clearTimeout(searchTimerRef.current)

    if (!q.trim()) {
      setSearchCandidates([])
      setShowSearchDropdown(false)
      setHighlightNodes(null)
      setSearchMatches([])
      return
    }

    searchTimerRef.current = setTimeout(() => {
      const results = smartSearch(q, data.nodes)
      setSearchCandidates(results)
      setShowSearchDropdown(results.length > 0)

      if (results.length > 0) {
        const matchIds = new Set(results.map(r => r.id))
        setHighlightNodes(matchIds)
        const matchNodes = data.nodes.filter(n => matchIds.has(n.id))
        setSearchMatches(matchNodes)
        setSearchMatchIdx(0)
      } else {
        setHighlightNodes(null)
        setSearchMatches([])
      }
    }, 300)
  }, [data.nodes])

  // 후보 클릭 핸들러
  const handleCandidateClick = useCallback((candidate: SearchCandidate) => {
    setShowSearchDropdown(false)
    setHighlightNodes(new Set([candidate.id]))
    const node = data.nodes.find(n => n.id === candidate.id) as AnyNode | undefined
    if (node && fgRef.current) {
      fgRef.current.centerAt(node.x || 0, node.y || 0, 400)
      fgRef.current.zoom(3, 400)
    }
  }, [data.nodes])

  // 검색 매치 간 이동 (위/아래 화살표)
  const navigateSearchMatch = useCallback(
    (direction: 1 | -1) => {
      if (searchMatches.length === 0) return
      const nextIdx = (searchMatchIdx + direction + searchMatches.length) % searchMatches.length
      setSearchMatchIdx(nextIdx)
      const node = searchMatches[nextIdx] as AnyNode
      setSelectedNode(searchMatches[nextIdx])
      if (fgRef.current) {
        fgRef.current.centerAt(node.x || 0, node.y || 0, 600)
        fgRef.current.zoom(3, 600)
      }
    },
    [searchMatches, searchMatchIdx],
  )

  // 노드 타입 표시/숨김 토글
  const toggleType = useCallback((type: string) => {
    setHiddenTypes(prev => {
      const next = new Set(prev)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }, [])

  // 연결 노드 클릭 시 해당 노드로 카메라 이동
  const handleConnectionClick = useCallback(
    (nodeId: string) => {
      const target = filteredData.nodes.find(n => n.id === nodeId) as AnyNode | undefined
      if (!target || !fgRef.current) return
      setSelectedNode(target)
      fgRef.current.centerAt(target.x || 0, target.y || 0, 600)
      fgRef.current.zoom(4, 600)
    },
    [filteredData.nodes],
  )

  // 선택된 노드 주제로 채팅 시작
  const handleStartChat = useCallback(
    (node: GraphNode) => {
      navigate('/chat', { state: { topic: node.name || node.id } })
    },
    [navigate],
  )

  // 선택된 노드의 연결 관계 목록
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

  // 인사이트 패널 토글
  const handleToggleInsights = useCallback(() => {
    const next = !showInsights
    setShowInsights(next)
    if (next && !insights && !insightsLoading) {
      loadInsights()
    }
    // 인사이트 열 때는 노드 상세 패널 닫기
    if (next) setSelectedNode(null)
  }, [showInsights, insights, insightsLoading, loadInsights])

  // 클러스터 선택 → centroid 계산 → 카메라 줌
  const handleClusterSelect = useCallback(
    (cluster: ClusterInfo) => {
      const clusterNodes = filteredData.nodes.filter(n =>
        cluster.entities.includes(n.name || n.id),
      ) as AnyNode[]

      if (clusterNodes.length === 0 || !fgRef.current) return

      const cx = clusterNodes.reduce((s, n) => s + (n.x || 0), 0) / clusterNodes.length
      const cy = clusterNodes.reduce((s, n) => s + (n.y || 0), 0) / clusterNodes.length

      fgRef.current.centerAt(cx, cy, 600)
      fgRef.current.zoom(3, 600)

      // 클러스터 노드만 하이라이트
      const clusterIds = new Set(clusterNodes.map(n => n.id))
      setHighlightNodes(clusterIds)
    },
    [filteredData.nodes],
  )

  // 노드 이름으로 검색+포커스
  const focusNodeByName = useCallback(
    (name: string) => {
      const node = filteredData.nodes.find(n => (n.name || n.id) === name) as AnyNode | undefined
      if (!node || !fgRef.current) return
      setSelectedNode(node)
      fgRef.current.centerAt(node.x || 0, node.y || 0, 600)
      fgRef.current.zoom(4, 600)
    },
    [filteredData.nodes],
  )

  const isEmptyGraph = !loading && data.nodes.length === 0

  return (
    <div className="graph-view-container">
      {/* 검색 바 */}
      {!loading && !isEmptyGraph && (
        <div className="graph-search">
          <div className="search-input-wrapper">
            <svg className="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" />
              <path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="text"
              placeholder="노드 검색..."
              value={searchQuery}
              onChange={handleSearchChange}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  if (searchMatches.length > 0 && searchQuery.trim()) {
                    navigateSearchMatch(1)
                  }
                }
                if (e.key === 'ArrowDown' && searchMatches.length > 0) {
                  e.preventDefault()
                  navigateSearchMatch(1)
                }
                if (e.key === 'ArrowUp' && searchMatches.length > 0) {
                  e.preventDefault()
                  navigateSearchMatch(-1)
                }
                if (e.key === 'Escape') {
                  setSearchQuery('')
                  setSearchCandidates([])
                  setShowSearchDropdown(false)
                  setHighlightNodes(null)
                  setSearchMatches([])
                }
              }}
              onBlur={() => {
                // 드롭다운 클릭이 먼저 처리되도록 약간의 딜레이
                setTimeout(() => setShowSearchDropdown(false), 200)
              }}
            />
            {searchMatches.length > 0 && (
              <span className="search-match-count">
                {searchMatchIdx + 1}/{searchMatches.length}
              </span>
            )}
          </div>
          {showSearchDropdown && searchCandidates.length > 0 && (
            <div className="search-dropdown">
              {searchCandidates.map(c => (
                <button
                  key={c.id}
                  className="search-dropdown-item"
                  onClick={() => handleCandidateClick(c)}
                >
                  <span className="search-item-name">{c.name}</span>
                  <span className="search-item-meta">
                    <span className="search-item-type">{NODE_TYPE_KO[c.label] || c.label}</span>
                    <span className="search-item-val">연결 {c.val}</span>
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 통계 정보 */}
      {!loading && !isEmptyGraph && (
        <div className="graph-stats">
          노드 {filteredData.nodes.length}개 &middot; 연결 {filteredData.links.length}개
        </div>
      )}

      {/* 로딩 상태 */}
      {loading && (
        <div className="graph-loader">
          <div className="loader-spinner" />
          <p>지식 그래프 로딩 중...</p>
        </div>
      )}

      {/* 빈 상태 */}
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
          <h3>지식 그래프가 비어있습니다</h3>
          <p>
            메모리를 추가하면 지식 그래프가 자동으로 생성됩니다.<br />
            엔티티와 연결이 자동으로 추출됩니다.
          </p>
          <button onClick={() => navigate('/memories')} className="add-memory-btn">
            + 메모리 추가
          </button>
        </div>
      )}

      {/* 2D 포스 그래프 */}
      {!loading && !isEmptyGraph && (
        <ForceGraph2D
          ref={fgRef}
          graphData={filteredData}
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={(node: AnyNode, color, ctx) => {
            const size = Math.max(3, Math.sqrt(node.val || 1) * 2.5)
            ctx.beginPath()
            ctx.arc(node.x || 0, node.y || 0, size + 2, 0, 2 * Math.PI)
            ctx.fillStyle = color
            ctx.fill()
          }}
          linkColor={(link: GraphLink) =>
            highlightLinks.has(getLinkKey(link))
              ? (bgColor === '#1a1a1a' ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.5)')
              : (bgColor === '#1a1a1a' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)')
          }
          linkWidth={(link: GraphLink) => (highlightLinks.has(getLinkKey(link)) ? 2 : 0.5)}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkDirectionalParticles={(link: GraphLink) =>
            highlightLinks.has(getLinkKey(link)) ? 2 : 0
          }
          linkDirectionalParticleWidth={2}
          linkDirectionalParticleSpeed={0.008}
          backgroundColor={bgColor}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          onBackgroundClick={handleBackgroundClick}
          cooldownTicks={120}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          onZoom={handleZoom}
          onEngineStop={() => {
            if (cameraRestoredRef.current) return
            cameraRestoredRef.current = true
            const saved = sessionStorage.getItem(CAMERA_STORAGE_KEY)
            if (saved) {
              try {
                const { k, x, y } = JSON.parse(saved)
                fgRef.current?.zoom(k, 0)
                fgRef.current?.centerAt(-x / k, -y / k, 0)
              } catch { fgRef.current?.zoomToFit(400, 40) }
            } else {
              fgRef.current?.zoomToFit(400, 40)
            }
          }}
        />
      )}

      {/* 범례 */}
      {!loading && nodeTypes.length > 0 && (
        <GraphLegend
          nodeTypes={nodeTypes}
          hiddenTypes={hiddenTypes}
          onToggleType={toggleType}
        />
      )}

      {/* 인사이트 토글 버튼 */}
      {!loading && !isEmptyGraph && (
        <div className="graph-insight-controls">
          <button
            className={`insight-toggle-btn ${showInsights ? 'active' : ''}`}
            onClick={handleToggleInsights}
            title="인사이트 패널"
          >
            <Lightbulb size={18} />
          </button>
          {insights?.clusters && insights.clusters.length > 0 && (
            <button
              className={`cluster-color-btn ${clusterColorMode ? 'active' : ''}`}
              onClick={() => setClusterColorMode(!clusterColorMode)}
              title="클러스터 색상 모드"
            >
              클러스터
            </button>
          )}
        </div>
      )}

      {/* 인사이트 패널 */}
      {showInsights && !selectedNode && (
        <GraphInsightPanel
          insights={insights}
          loading={insightsLoading}
          onClusterSelect={handleClusterSelect}
          onIsolatedNodeClick={focusNodeByName}
          onHubNodeClick={focusNodeByName}
          onConnectionCreated={() => {
            fetchGraphData()
            loadInsights()
          }}
        />
      )}

      {/* 선택된 노드 상세 패널 */}
      {selectedNode && (
        <NodeInfoPanel
          node={selectedNode}
          connections={selectedConnections}
          relatedMemories={relatedMemories}
          isLoadingMemories={isLoadingMemories}
          onClose={() => setSelectedNode(null)}
          onConnectionClick={handleConnectionClick}
          onMemoryClick={setSelectedMemoryId}
          onStartChat={handleStartChat}
          onViewMemories={() => navigate('/memories')}
        />
      )}

      {/* 조작 안내 */}
      {!loading && !isEmptyGraph && (
        <div className="graph-controls">
          <span>드래그: 이동</span>
          <span>스크롤: 확대/축소</span>
          <span>클릭: 포커스</span>
        </div>
      )}

      {/* 줌 컨트롤 패널 */}
      {!loading && !isEmptyGraph && (
        <div className="graph-zoom-controls">
          <button className="graph-zoom-btn" onClick={handleZoomToFit} title="전체 보기">
            <Maximize size={16} />
          </button>
          <button className="graph-zoom-btn" onClick={handleZoomIn} title="확대">
            <ZoomIn size={16} />
          </button>
          <button className="graph-zoom-btn" onClick={handleZoomOut} title="축소">
            <ZoomOut size={16} />
          </button>
        </div>
      )}

      {/* 첫 방문 온보딩 오버레이 */}
      {showOnboarding && !loading && !isEmptyGraph && (
        <div className="graph-onboarding-overlay" onClick={dismissOnboarding}>
          <div className="graph-onboarding-card" onClick={e => e.stopPropagation()}>
            <h3>지식 그래프 사용법</h3>
            <ul>
              <li>드래그로 화면을 이동할 수 있습니다</li>
              <li>스크롤(또는 핀치)로 확대/축소할 수 있습니다</li>
              <li>노드를 클릭하면 상세 정보를 볼 수 있습니다</li>
              <li>더블클릭하면 관련 메모리를 열 수 있습니다</li>
            </ul>
            <button className="graph-onboarding-btn" onClick={dismissOnboarding}>
              확인
            </button>
          </div>
        </div>
      )}

      {/* 메모리 상세 모달 */}
      {selectedMemoryId && (
        <MemoryDetailModal
          memoryId={selectedMemoryId}
          onClose={() => setSelectedMemoryId(null)}
          onDeleted={() => {
            setSelectedMemoryId(null)
            fetchGraphData()
          }}
        />
      )}
    </div>
  )
}
