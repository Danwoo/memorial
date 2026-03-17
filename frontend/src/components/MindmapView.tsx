import { useEffect, useState, useRef, useCallback, useMemo } from 'react'
import { useResizePanel } from '../hooks/useResizePanel'
import { useNavigate, useLocation } from 'react-router-dom'
import ForceGraph2D from 'react-force-graph-2d'
import { Lightbulb, Maximize, ZoomIn, ZoomOut, Expand } from 'lucide-react'
import type { MindmapNode, MindmapLink, MindmapData, SearchResult, MindmapInsights, ClusterInfo } from '../types'
import { useTheme } from '../contexts/ThemeContext'
import { useToast } from '../contexts/ToastContext'
import { useAuth } from '../contexts/AuthContext'
import { demoPath } from '../utils/demoPath'
import { fetchMindmap, fetchMindmapInsights, searchScraps, fetchEgoMindmap, fetchEgoDefault, rebuildGraph } from '../api'
import { getViewCache, setViewCache, CACHE_KEYS } from '../utils/viewCache'
import ScrapDetailModal from './ScrapDetailModal'
import MindmapInsightPanel, { CLUSTER_COLORS } from './MindmapInsightPanel'
import NodeInfoPanel from './mindmap/NodeInfoPanel'
import GraphLegend from './mindmap/GraphLegend'
import { NODE_COLORS, NODE_TYPE_KO, toKo } from './mindmap/mindmapConstants'
import { smartSearch, type SearchCandidate } from '../utils/searchUtils'
import './MindmapView.css'

type AnyNode = MindmapNode & { x?: number; y?: number; vx?: number; vy?: number; fx?: number; fy?: number }

const CAMERA_STORAGE_KEY = 'memoir-mindmap-camera'
const ONBOARDING_KEY = 'memoir-mindmap-visited'

export default function MindmapView() {
  const navigate = useNavigate()
  const location = useLocation()
  const { resolvedTheme } = useTheme()
  const toast = useToast()
  const { user } = useAuth()
  const userId = user?.id ?? ''
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null)
  const cameraRestoredRef = useRef(false)

  const containerRef = useRef<HTMLDivElement>(null)
  const [dimensions, setDimensions] = useState({ width: 800, height: 600 })

  const [data, setData] = useState<MindmapData>({ nodes: [], links: [] })
  const [maxVal, setMaxVal] = useState(1)
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<MindmapNode | null>(null)
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set())
  const [highlightNodes, setHighlightNodes] = useState<Set<string> | null>(null)
  const [searchQuery, setSearchQuery] = useState('')
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())

  // Ego 그래프 모드
  const [viewMode, setViewMode] = useState<'ego' | 'full'>('ego')
  const [egoCenter, setEgoCenter] = useState<string | null>(null)
  const [egoDepth, setEgoDepth] = useState(1)

  // 관련 스크랩 조회
  const [relatedScraps, setRelatedScraps] = useState<SearchResult[]>([])
  const [isLoadingScraps, setIsLoadingScraps] = useState(false)
  const [selectedScrapId, setSelectedScrapId] = useState<string | null>(null)

  // 검색 결과 하이라이트
  const [searchMatches, setSearchMatches] = useState<MindmapNode[]>([])
  const [searchMatchIdx, setSearchMatchIdx] = useState(0)
  const [searchCandidates, setSearchCandidates] = useState<SearchCandidate[]>([])
  const [showSearchDropdown, setShowSearchDropdown] = useState(false)

  // 온보딩 코치마크
  const [showOnboarding, setShowOnboarding] = useState(() => !localStorage.getItem(ONBOARDING_KEY))
  const showOnboardingRef = useRef(showOnboarding)
  showOnboardingRef.current = showOnboarding

  // 호버 툴팁
  const [hoverNode, setHoverNode] = useState<{ node: MindmapNode; x: number; y: number } | null>(null)
  const hoverTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const mousePos = useRef({ x: 0, y: 0 })

  // 줌 레벨 기반 라벨 표시 제어
  const [zoomTier, setZoomTier] = useState<'far' | 'mid' | 'close'>('far')
  const zoomTierRef = useRef<'far' | 'mid' | 'close'>('far')
  const currentZoomRef = useRef(1)
  const labelBoundsRef = useRef<Array<{ x1: number; y1: number; x2: number; y2: number }>>([])
  const lastFrameRef = useRef(0)

  // 인사이트 패널
  const [insights, setInsights] = useState<MindmapInsights | null>(null)
  const [insightsLoading, setInsightsLoading] = useState(false)
  const [showInsights, setShowInsights] = useState(false)
  const { vw: insightVw, onMouseDown: onInsightResize } = useResizePanel(19, 13, 35, 'left', 'mindmap-insight-vw')
  const [clusterColorMode, setClusterColorMode] = useState(false)

  const bgColor = resolvedTheme === 'dark' ? '#1a1a1a' : '#ffffff'
  const textColor = resolvedTheme === 'dark' ? '#f0f0f0' : '#1a1a1a'
  const labelBg = resolvedTheme === 'dark' ? 'rgba(0,0,0,0.75)' : 'rgba(255,255,255,0.92)'

  // 노드 가공 헬퍼
  const processNodes = useCallback((json: { nodes: { id: string; label: string; properties: Record<string, unknown>; name?: string; group?: string; val?: number }[]; links: MindmapLink[] }) => {
    const processedNodes: MindmapNode[] = json.nodes.map(n => ({
      ...n,
      val: n.val || 1,
      color: NODE_COLORS[n.label] || NODE_COLORS['default'],
      name: n.name || (n.properties?.name as string) || (n.properties?.title as string) || n.id,
    }))
    const mv = processedNodes.reduce((max, n) => Math.max(max, n.val || 1), 1)
    return { nodes: processedNodes, links: json.links, mv }
  }, [])

  // 전체 그래프 조회 (인사이트 패널 등에서 사용)
  const fetchMindmapData = useCallback(async () => {
    try {
      setLoading(true)
      const json = await fetchMindmap(300)
      const { nodes, links, mv } = processNodes(json)
      setMaxVal(mv)
      setData({ nodes, links })
    } catch (err) {
      console.error('마인드맵 데이터 로딩 실패:', err)
      toast.error('지식 마인드맵을 불러오지 못했습니다')
    } finally {
      setLoading(false)
    }
  }, [toast, processNodes])

  const loadInsights = useCallback(async () => {
    setInsightsLoading(true)
    try {
      const data = await fetchMindmapInsights()
      setInsights(data)
    } catch {
      setInsights(null)
    } finally {
      setInsightsLoading(false)
    }
  }, [])

  // 세션당 한 번만 자동 재구축 시도 (서버 마이그레이션 후 빈 그래프 복구)
  const rebuildAttemptedRef = useRef(false)

  // Ego/Full 모드에 따른 데이터 로딩 (userId 스코핑 캐시)
  useEffect(() => {
    let cancelled = false

    if (!userId) return

    const cacheKey = `${CACHE_KEYS.GRAPH_PREFIX}${viewMode}:${egoCenter ?? 'default'}:${egoDepth}`
    const cached = getViewCache<{ data: MindmapData; maxVal: number; egoCenter?: string | null }>(userId, cacheKey)

    // 캐시가 유효하면 즉시 표시
    if (cached) {
      setData(cached.data)
      setMaxVal(cached.maxVal)
      if (cached.egoCenter && !egoCenter) setEgoCenter(cached.egoCenter)
      setLoading(false)
      cameraRestoredRef.current = false
      return
    }

    setLoading(true)
    setSelectedNode(null)
    setHighlightNodes(null)
    setHighlightLinks(new Set())

    const loadData = async () => {
      try {
        let result: { nodes: { id: string; label: string; properties: Record<string, unknown>; name?: string; group?: string; val?: number }[]; links: MindmapLink[]; center_node?: string | null }

        if (viewMode === 'ego') {
          if (egoCenter) {
            result = await fetchEgoMindmap(egoCenter, egoDepth)
          } else {
            result = await fetchEgoDefault()
            if (!cancelled && result.center_node) {
              setEgoCenter(result.center_node)
            }
          }
        } else {
          result = await fetchMindmap(300)
        }

        if (!cancelled) {
          const { nodes, links, mv } = processNodes(result)

          // 노드가 0개이고 첫 시도라면 서버 그래프 재구축 시도 (EC2 이전 후 빈 그래프 복구)
          if (nodes.length === 0 && !rebuildAttemptedRef.current) {
            rebuildAttemptedRef.current = true
            try {
              const rebuildResult = await rebuildGraph()
              if (rebuildResult.processed > 0 && !cancelled) {
                // 재구축 성공 → 데이터 다시 로드
                const freshResult = viewMode === 'ego' ? await fetchEgoDefault() : await fetchMindmap(300)
                if (!cancelled) {
                  const { nodes: freshNodes, links: freshLinks, mv: freshMv } = processNodes(freshResult)
                  setMaxVal(freshMv)
                  setData({ nodes: freshNodes, links: freshLinks })
                  if ((freshResult as { center_node?: string | null }).center_node) {
                    setEgoCenter((freshResult as { center_node?: string | null }).center_node ?? null)
                  }
                  cameraRestoredRef.current = false
                  const finalCacheKey = `${CACHE_KEYS.GRAPH_PREFIX}${viewMode}:${(freshResult as { center_node?: string | null }).center_node ?? egoCenter ?? 'default'}:${egoDepth}`
                  setViewCache(userId, finalCacheKey, { data: { nodes: freshNodes, links: freshLinks }, maxVal: freshMv, egoCenter: (freshResult as { center_node?: string | null }).center_node ?? egoCenter })
                }
                return
              }
            } catch {
              // 재구축 실패는 조용히 무시 — 빈 상태로 표시
            }
          }

          setMaxVal(mv)
          setData({ nodes, links })
          cameraRestoredRef.current = false

          // 캐시 저장 (빈 그래프는 캐싱하지 않음 — 재구축 기회 보존)
          if (nodes.length > 0) {
            const finalCacheKey = `${CACHE_KEYS.GRAPH_PREFIX}${viewMode}:${result.center_node ?? egoCenter ?? 'default'}:${egoDepth}`
            setViewCache(userId, finalCacheKey, { data: { nodes, links }, maxVal: mv, egoCenter: result.center_node ?? egoCenter })
          }
        }
      } catch {
        if (!cancelled) toast.error('마인드맵을 불러올 수 없습니다')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadData()
    return () => { cancelled = true }
  }, [viewMode, egoCenter, egoDepth, userId, toast, processNodes])

  // 마우스 좌표 트래킹 (호버 툴팁용)
  useEffect(() => {
    const handler = (e: MouseEvent) => { mousePos.current = { x: e.clientX, y: e.clientY } }
    window.addEventListener('mousemove', handler)
    return () => window.removeEventListener('mousemove', handler)
  }, [])

  // 컨테이너 리사이즈 감지 → 캔버스 크기 동기화
  useEffect(() => {
    const el = containerRef.current
    if (!el) return
    const ro = new ResizeObserver(entries => {
      const { width, height } = entries[0].contentRect
      if (width > 0 && height > 0) {
        setDimensions({ width: Math.floor(width), height: Math.floor(height) })
      }
    })
    ro.observe(el)
    return () => ro.disconnect()
  }, [])

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

  // 온보딩 닫기
  const dismissOnboarding = useCallback(() => {
    setShowOnboarding(false)
    localStorage.setItem(ONBOARDING_KEY, '1')
  }, [])

  // 카메라 상태 sessionStorage 저장 (디바운스 500ms)
  const cameraSaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const handleZoom = useCallback(({ k, x, y }: { k: number; x: number; y: number }) => {
    if (showOnboardingRef.current) dismissOnboarding()
    currentZoomRef.current = k
    // 줌 구간이 변경될 때만 state 업데이트 (불필요한 리렌더 방지)
    const tier: 'far' | 'mid' | 'close' = k < 1.0 ? 'far' : k < 2.0 ? 'mid' : 'close'
    if (tier !== zoomTierRef.current) {
      zoomTierRef.current = tier
      setZoomTier(tier)
    }
    if (cameraSaveTimerRef.current) clearTimeout(cameraSaveTimerRef.current)
    cameraSaveTimerRef.current = setTimeout(() => {
      sessionStorage.setItem(CAMERA_STORAGE_KEY, JSON.stringify({ k, x, y }))
    }, 500)
  }, [dismissOnboarding])

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

  // 선택 노드 변경 시 관련 스크랩 조회
  useEffect(() => {
    if (!selectedNode) {
      setRelatedScraps([])
      return
    }
    let cancelled = false
    const fetchRelated = async () => {
      setIsLoadingScraps(true)
      try {
        const res = await searchScraps({ q: selectedNode.name || selectedNode.id, limit: 5 })
        if (!cancelled) setRelatedScraps(res.results ?? [])
      } catch {
        if (!cancelled) setRelatedScraps([])
      } finally {
        if (!cancelled) setIsLoadingScraps(false)
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

  // 줌 레벨별 라벨 표시 노드 제한
  const sortedNodesByVal = useMemo(
    () => [...filteredData.nodes].sort((a, b) => (b.val || 1) - (a.val || 1)),
    [filteredData.nodes],
  )

  const labelNodeLimit = useMemo(() => {
    if (zoomTier === 'far') return 15
    if (zoomTier === 'mid') return 40
    return Infinity
  }, [zoomTier])

  const topNodeIds = useMemo(
    () => new Set(sortedNodesByVal.slice(0, labelNodeLimit).map(n => n.id)),
    [sortedNodesByVal, labelNodeLimit],
  )

  // 범례용 고유 노드 타입 목록
  const nodeTypes = useMemo(
    () => [...new Set(data.nodes.map(n => n.label))].sort(),
    [data.nodes],
  )

  // 클러스터 색상 모드에서 노드 색상 결정
  const getNodeColor = useCallback(
    (node: MindmapNode): string => {
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
    // 새 프레임 시작 시 라벨 바운드 리스트 초기화
    const now = performance.now()
    if (now - lastFrameRef.current > 10) {
      labelBoundsRef.current = []
      lastFrameRef.current = now
    }

    const val = node.val || 1
    const MIN_NODE_SIZE = 3
    const MAX_NODE_SIZE = 15
    const normalizedVal = Math.log2(val + 1) / Math.log2(maxVal + 1)
    const size = MIN_NODE_SIZE + normalizedVal * (MAX_NODE_SIZE - MIN_NODE_SIZE)
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

    // 라벨 표시 조건: 줌 레벨별 상위 노드만 + 충돌 감지
    const showLabel = isHighlighted && (
      globalScale > 3.0 ||
      (globalScale > 0.6 && topNodeIds.has(node.id))
    )
    if (showLabel) {
      const fontSize = Math.max(3.5, size * 0.55) / globalScale
      ctx.font = `500 ${fontSize}px -apple-system, BlinkMacSystemFont, sans-serif`
      const textWidth = ctx.measureText(label).width
      const padding = 2 / globalScale
      const labelY = (node.y || 0) + size + 2 / globalScale

      const bounds = {
        x1: (node.x || 0) - textWidth / 2 - padding,
        y1: labelY - padding,
        x2: (node.x || 0) + textWidth / 2 + padding,
        y2: labelY + fontSize + padding,
      }

      // 충돌 체크
      const hasCollision = labelBoundsRef.current.some(
        b => !(bounds.x2 < b.x1 || bounds.x1 > b.x2 || bounds.y2 < b.y1 || bounds.y1 > b.y2)
      )

      if (!hasCollision) {
        labelBoundsRef.current.push(bounds)

        // 라벨 배경
        ctx.fillStyle = labelBg
        ctx.globalAlpha = isHighlighted ? 0.85 : 0.3
        ctx.fillRect(bounds.x1, bounds.y1, textWidth + padding * 2, fontSize + padding * 2)
        ctx.globalAlpha = 1

        // 라벨 텍스트
        ctx.textAlign = 'center'
        ctx.textBaseline = 'top'
        ctx.fillStyle = textColor
        ctx.globalAlpha = isHighlighted ? 1 : 0.2
        ctx.fillText(label, node.x || 0, labelY)
        ctx.globalAlpha = 1
      }
    }
  }, [clusterColorMode, getNodeColor, highlightNodes, labelBg, textColor, maxVal, topNodeIds])

  // 하이라이트 매칭용 링크 키 생성
  const getLinkKey = useCallback((link: MindmapLink) => {
    const sid = typeof link.source === 'object' ? link.source.id : link.source
    const tid = typeof link.target === 'object' ? link.target.id : link.target
    return `${sid}-${tid}`
  }, [])

  // 호버 시 연결된 노드/링크 하이라이트 + 툴팁
  const handleNodeHover = useCallback((node: AnyNode | null) => {
    if (showOnboardingRef.current) dismissOnboarding()

    // 호버 툴팁 (200ms 딜레이)
    if (hoverTimerRef.current) clearTimeout(hoverTimerRef.current)
    if (node && node.id !== selectedNode?.id) {
      hoverTimerRef.current = setTimeout(() => {
        setHoverNode({
          node,
          x: mousePos.current.x,
          y: mousePos.current.y,
        })
      }, 200)
    } else {
      setHoverNode(null)
    }

    // 하이라이트 로직
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
  }, [filteredData.links, dismissOnboarding, selectedNode?.id])

  // 더블클릭 감지를 위한 ref
  const lastClickRef = useRef<{ id: string; time: number }>({ id: '', time: 0 })

  // 클릭 시 해당 노드로 이동, 더블클릭 시 메모리 상세 모달
  const handleNodeClick = useCallback((node: AnyNode) => {
    if (showOnboardingRef.current) dismissOnboarding()
    setHoverNode(null)
    const now = Date.now()
    const last = lastClickRef.current
    if (last.id === node.id && now - last.time < 400) {
      // 더블클릭: 관련 스크랩에서 첫 번째 결과를 모달로 열기
      searchScraps({ q: node.name || node.id, limit: 1 }).then(res => {
        const first = res.results?.[0]
        if (first) setSelectedScrapId(first.id)
      }).catch(() => {})
      lastClickRef.current = { id: '', time: 0 }
      return
    }
    lastClickRef.current = { id: node.id, time: now }

    setSelectedNode(node)
    if (showInsights) setShowInsights(false)
    // Ego 모드에서 다른 노드 클릭 시 중심 전환
    if (viewMode === 'ego' && node.name !== egoCenter) {
      setEgoCenter(node.name || node.id)
      setEgoDepth(1)
    }
    // 2D 카메라 이동
    if (fgRef.current) {
      fgRef.current.centerAt(node.x || 0, node.y || 0, 600)
      fgRef.current.zoom(4, 600)
    }
  }, [showInsights, dismissOnboarding, viewMode, egoCenter])

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
    (node: MindmapNode) => {
      const neighbors = filteredData.links
        .filter(l => {
          const sid = typeof l.source === 'object' ? l.source.id : l.source
          const tid = typeof l.target === 'object' ? l.target.id : l.target
          return sid === node.id || tid === node.id
        })
        .slice(0, 10)
        .map(l => {
          const sid = typeof l.source === 'object' ? l.source.id : l.source
          const tid = typeof l.target === 'object' ? l.target.id : l.target
          const otherId = sid === node.id ? tid : sid
          const other = filteredData.nodes.find(n => n.id === otherId)
          return {
            name: other?.name || String(otherId),
            label: other?.label || '',
            relation_type: l.type || 'RELATED_TO',
          }
        })

      navigate(demoPath('/diary'), {
        state: {
          openSocrates: true,
          topic: node.name || node.id,
          sourceContext: {
            type: 'mindmap' as const,
            title: node.name,
            graph_neighbors: neighbors,
          },
        },
      })
    },
    [navigate, filteredData],
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

  const isEmptyMindmap = !loading && data.nodes.length === 0

  return (
    <div className="mindmap-view-container" ref={containerRef}>
      {/* Ego/전체 모드 토글 */}
      {!loading && !isEmptyMindmap && (
        <div className="mindmap-mode-toggle">
          <button
            className={`mindmap-mode-btn ${viewMode === 'ego' ? 'active' : ''}`}
            onClick={() => { setViewMode('ego'); setEgoCenter(null); setEgoDepth(1) }}
          >
            로컬
          </button>
          <button
            className={`mindmap-mode-btn ${viewMode === 'full' ? 'active' : ''}`}
            onClick={() => setViewMode('full')}
          >
            전체
          </button>
        </div>
      )}

      {/* Ego 중심 노드 정보 바 */}
      {viewMode === 'ego' && egoCenter && !loading && (
        <div className="ego-info-bar">
          <span className="ego-center-name">{egoCenter}</span>
          <span>중심 · {egoDepth === 1 ? '1단계' : '2단계'}</span>
          {egoDepth < 2 && (
            <button className="ego-expand-btn" onClick={() => setEgoDepth(2)}>
              <Expand size={12} /> 더 보기
            </button>
          )}
        </div>
      )}

      {/* 검색 바 */}
      {!loading && !isEmptyMindmap && (
        <div className="mindmap-search">
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
      {!loading && !isEmptyMindmap && (
        <div className="mindmap-stats">
          노드 {filteredData.nodes.length}개 &middot; 연결 {filteredData.links.length}개
        </div>
      )}

      {/* 로딩 상태 */}
      {loading && (
        <div className="mindmap-loader">
          <div className="loader-spinner" />
          <p>지식 마인드맵 로딩 중...</p>
        </div>
      )}

      {/* 빈 상태 */}
      {isEmptyMindmap && (
        <div className="mindmap-empty">
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
          <h3>지식 마인드맵이 비어있습니다</h3>
          <p>
            스크랩을 추가하면 지식 마인드맵이 자동으로 생성됩니다.<br />
            엔티티와 연결이 자동으로 추출됩니다.
          </p>
          <button onClick={() => navigate(demoPath('/scraps'))} className="add-scrap-btn">
            + 스크랩 추가
          </button>
        </div>
      )}

      {/* 2D 포스 그래프 */}
      {!loading && !isEmptyMindmap && (
        <ForceGraph2D
          ref={fgRef}
          width={dimensions.width}
          height={dimensions.height}
          graphData={filteredData}
          nodeCanvasObject={nodeCanvasObject}
          nodePointerAreaPaint={(node: AnyNode, color, ctx) => {
            const val = node.val || 1
            const normalizedVal = Math.log2(val + 1) / Math.log2(maxVal + 1)
            const size = 3 + normalizedVal * 12
            ctx.beginPath()
            ctx.arc(node.x || 0, node.y || 0, size + 2, 0, 2 * Math.PI)
            ctx.fillStyle = color
            ctx.fill()
          }}
          linkColor={(link: MindmapLink) =>
            highlightLinks.has(getLinkKey(link))
              ? (bgColor === '#1a1a1a' ? 'rgba(255,255,255,0.7)' : 'rgba(0,0,0,0.5)')
              : (bgColor === '#1a1a1a' ? 'rgba(255,255,255,0.08)' : 'rgba(0,0,0,0.08)')
          }
          linkWidth={(link: MindmapLink) => (highlightLinks.has(getLinkKey(link)) ? 2 : 0.5)}
          linkDirectionalArrowLength={4}
          linkDirectionalArrowRelPos={1}
          linkDirectionalParticles={(link: MindmapLink) =>
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
              // 밀집 영역 중심 줌: 노드 좌표 평균으로 centerAt + 적절한 줌
              const nodes = filteredData.nodes as AnyNode[]
              if (nodes.length === 0) return
              const withPos = nodes.filter(n => n.x !== undefined && n.y !== undefined)
              if (withPos.length === 0) {
                fgRef.current?.zoomToFit(400, 40)
                return
              }
              const cx = withPos.reduce((s, n) => s + (n.x || 0), 0) / withPos.length
              const cy = withPos.reduce((s, n) => s + (n.y || 0), 0) / withPos.length
              fgRef.current?.centerAt(cx, cy, 400)
              fgRef.current?.zoom(2.5, 400)
            }
          }}
        />
      )}

      {/* 호버 툴팁 */}
      {hoverNode && (
        <div
          className="mindmap-hover-tooltip"
          style={{
            left: hoverNode.x + 12,
            top: hoverNode.y - 10,
          }}
        >
          <span className="hover-tooltip-name">{hoverNode.node.name || hoverNode.node.id}</span>
          <span className="hover-tooltip-meta">
            {toKo(hoverNode.node.label, NODE_TYPE_KO)} &middot; 연결 {hoverNode.node.val || 1}개
          </span>
        </div>
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
      {!loading && !isEmptyMindmap && (
        <div className="mindmap-insight-controls">
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
        <MindmapInsightPanel
          insights={insights}
          loading={insightsLoading}
          onClusterSelect={handleClusterSelect}
          onIsolatedNodeClick={focusNodeByName}
          onHubNodeClick={focusNodeByName}
          onConnectionCreated={() => {
            fetchMindmapData()
            loadInsights()
          }}
          panelWidth={`${insightVw}vw`}
          onPanelResize={onInsightResize}
        />
      )}

      {/* 선택된 노드 상세 패널 */}
      {selectedNode && (
        <NodeInfoPanel
          node={selectedNode}
          connections={selectedConnections}
          relatedScraps={relatedScraps}
          isLoadingScraps={isLoadingScraps}
          onClose={() => setSelectedNode(null)}
          onConnectionClick={handleConnectionClick}
          onScrapClick={setSelectedScrapId}
          onStartChat={handleStartChat}
          onViewScraps={() => navigate(demoPath('/scraps'))}
        />
      )}

      {/* 조작 안내 (첫 방문 시 강조 코치마크 / 이후 간소 힌트) */}
      {!loading && !isEmptyMindmap && (
        <div className={`mindmap-controls ${showOnboarding ? 'mindmap-controls--onboarding' : ''}`}>
          {showOnboarding ? (
            <>
              <span>드래그로 이동</span>
              <span className="mindmap-controls-divider" />
              <span>스크롤로 확대/축소</span>
              <span className="mindmap-controls-divider" />
              <span>노드 클릭으로 상세 보기</span>
              <span className="mindmap-controls-divider" />
              <span>더블클릭으로 스크랩 열기</span>
            </>
          ) : (
            <>
              <span>드래그: 이동</span>
              <span>스크롤: 확대/축소</span>
              <span>클릭: 포커스</span>
            </>
          )}
        </div>
      )}

      {/* 줌 컨트롤 패널 */}
      {!loading && !isEmptyMindmap && (
        <div className="mindmap-zoom-controls">
          <button className="mindmap-zoom-btn" onClick={handleZoomToFit} title="전체 보기">
            <Maximize size={16} />
          </button>
          <button className="mindmap-zoom-btn" onClick={handleZoomIn} title="확대">
            <ZoomIn size={16} />
          </button>
          <button className="mindmap-zoom-btn" onClick={handleZoomOut} title="축소">
            <ZoomOut size={16} />
          </button>
        </div>
      )}

      {/* 메모리 상세 모달 */}
      {selectedScrapId && (
        <ScrapDetailModal
          scrapId={selectedScrapId}
          onClose={() => setSelectedScrapId(null)}
          onDeleted={() => {
            setSelectedScrapId(null)
            fetchMindmapData()
          }}
        />
      )}
    </div>
  )
}
