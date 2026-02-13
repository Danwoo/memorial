import { useEffect, useState, useRef, useCallback, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import ForceGraph3D from 'react-force-graph-3d'
import SpriteText from 'three-spritetext'
import * as THREE from 'three'
import { BookOpen } from 'lucide-react'
import type { GraphNode, GraphLink, GraphData, SearchResult } from '../types'
import { useTheme } from '../contexts/ThemeContext'
import { useToast } from '../contexts/ToastContext'
import { fetchGraph, searchMemories } from '../api'
import MemoryDetailModal from './MemoryDetailModal'
import './GraphView.css'

// 노드 타입별 색상 팔레트
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

// 노드 타입 한국어 매핑
const NODE_TYPE_KO: Record<string, string> = {
  Memory: '메모리',
  Entity: '엔티티',
  Concept: '개념',
  Person: '인물',
  Organization: '조직',
  Company: '회사',
  Technology: '기술',
  Platform: '플랫폼',
  Product: '제품',
  Location: '장소',
  Event: '이벤트',
  Topic: '주제',
  Idea: '아이디어',
  Framework: '프레임워크',
  Language: '언어',
  Tool: '도구',
}

// 관계 타입 한국어 매핑
const LINK_TYPE_KO: Record<string, string> = {
  RELATES_TO: '관련',
  MENTIONED_IN: '언급됨',
  MENTIONS: '언급',
  HAS_TAG: '태그',
  HAS_ENTITY: '엔티티 포함',
  ASSOCIATED_WITH: '연관',
  PART_OF: '소속',
  WORKS_AT: '근무',
  LOCATED_IN: '위치',
  CREATED_BY: '작성자',
  USED_IN: '사용됨',
  SIMILAR_TO: '유사',
  DEPENDS_ON: '의존',
  DERIVED_FROM: '파생',
  CONTAINS: '포함',
  BELONGS_TO: '소속',
}

// 한국어 변환 헬퍼
function toKo(type: string, map: Record<string, string>): string {
  return map[type] || type
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyNode = GraphNode & { x?: number; y?: number; z?: number; [k: string]: any }

export default function GraphView() {
  const navigate = useNavigate()
  const { resolvedTheme } = useTheme()
  const toast = useToast()
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const fgRef = useRef<any>(null)
  const nodeMaterials = useRef<Map<string, THREE.MeshLambertMaterial>>(new Map())

  const [data, setData] = useState<GraphData>({ nodes: [], links: [] })
  const [loading, setLoading] = useState(true)
  const [selectedNode, setSelectedNode] = useState<GraphNode | null>(null)
  const [highlightLinks, setHighlightLinks] = useState<Set<string>>(new Set())
  const [searchQuery, setSearchQuery] = useState('')
  const [hiddenTypes, setHiddenTypes] = useState<Set<string>>(new Set())

  // P2-11: 관련 메모리 조회
  const [relatedMemories, setRelatedMemories] = useState<SearchResult[]>([])
  const [isLoadingMemories, setIsLoadingMemories] = useState(false)
  const [selectedMemoryId, setSelectedMemoryId] = useState<string | null>(null)

  // P2-11: 검색 결과 하이라이트
  const [searchMatches, setSearchMatches] = useState<GraphNode[]>([])
  const [searchMatchIdx, setSearchMatchIdx] = useState(0)

  const bgColor = resolvedTheme === 'dark' ? '#1a1a1a' : '#ffffff'

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

  useEffect(() => {
    fetchGraphData()
  }, [fetchGraphData])

  // P2-11: 선택 노드 변경 시 관련 메모리 조회
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

  // 3D 노드 렌더링: 구체 + 라벨 스프라이트
  const nodeThreeObject = useCallback((node: AnyNode) => {
    const val = node.val || 1
    const size = Math.max(1.5, Math.sqrt(val) * 1.5)
    const color = node.color || NODE_COLORS['default']

    const group = new THREE.Group()

    // 구체 메시
    const geo = new THREE.SphereGeometry(size, 16, 12)
    const mat = new THREE.MeshLambertMaterial({
      color,
      transparent: true,
      opacity: 0.9,
    })
    const mesh = new THREE.Mesh(geo, mat)
    group.add(mesh)

    // 호버 하이라이트를 위해 재질 참조 저장
    nodeMaterials.current.set(node.id, mat)

    // 라벨 스프라이트
    const label = (node.name || node.id).substring(0, 24)
    const sprite = new SpriteText(label)
    sprite.color = bgColor === '#1a1a1a' ? '#ffffff' : '#1f1f1f'
    sprite.textHeight = Math.max(1.2, size * 0.5)
    sprite.backgroundColor = bgColor === '#1a1a1a' ? 'rgba(0,0,0,0.6)' : 'rgba(255,255,255,0.85)'
    sprite.padding = [0.5, 1] as unknown as number
    sprite.borderRadius = 1
    sprite.position.y = -(size + 2)
    group.add(sprite)

    return group
  }, [bgColor])

  // 하이라이트 매칭용 링크 키 생성
  const getLinkKey = useCallback((link: GraphLink) => {
    const sid = typeof link.source === 'object' ? link.source.id : link.source
    const tid = typeof link.target === 'object' ? link.target.id : link.target
    return `${sid}-${tid}`
  }, [])

  // 호버 시 연결된 노드/링크 하이라이트 (Three.js 재질 직접 조작)
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

      // 연결되지 않은 노드 흐리게 처리
      nodeMaterials.current.forEach((mat, id) => {
        mat.opacity = connectedIds.has(id) ? 1.0 : 0.1
      })

      setHighlightLinks(connectedLinkKeys)
    } else {
      // 모든 노드 불투명도 복원
      nodeMaterials.current.forEach(mat => {
        mat.opacity = 0.9
      })
      setHighlightLinks(new Set())
    }
  }, [filteredData.links])

  // 클릭 시 카메라를 해당 노드로 이동
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

  // 배경 클릭 시 선택 해제
  const handleBackgroundClick = useCallback(() => {
    setSelectedNode(null)
    setHighlightLinks(new Set())
    setSearchMatches([])
    nodeMaterials.current.forEach(mat => {
      mat.opacity = 0.9
    })
  }, [])

  // P2-11: 검색 하이라이트 — 모든 매치를 찾아 하이라이트
  const handleSearch = useCallback(
    (query: string) => {
      if (!query.trim()) {
        setSearchMatches([])
        setSearchMatchIdx(0)
        nodeMaterials.current.forEach(mat => { mat.opacity = 0.9 })
        return
      }
      const q = query.toLowerCase()
      const matches = filteredData.nodes.filter(n =>
        (n.name || n.id).toLowerCase().includes(q),
      )
      setSearchMatches(matches)
      setSearchMatchIdx(0)

      // 매치 노드만 밝게, 나머지 흐리게
      if (matches.length > 0) {
        const matchIds = new Set(matches.map(n => n.id))
        nodeMaterials.current.forEach((mat, id) => {
          mat.opacity = matchIds.has(id) ? 1.0 : 0.15
        })
        // 첫 매치로 카메라 이동
        const first = matches[0] as AnyNode
        if (fgRef.current) {
          const distance = 60
          const distRatio = 1 + distance / Math.hypot(first.x || 1, first.y || 1, first.z || 1)
          fgRef.current.cameraPosition(
            { x: (first.x || 0) * distRatio, y: (first.y || 0) * distRatio, z: (first.z || 0) * distRatio },
            { x: first.x || 0, y: first.y || 0, z: first.z || 0 },
            1000,
          )
        }
        setSelectedNode(matches[0])
      } else {
        nodeMaterials.current.forEach(mat => { mat.opacity = 0.9 })
      }
    },
    [filteredData.nodes],
  )

  // P2-11: 검색 매치 간 이동 (위/아래 화살표)
  const navigateSearchMatch = useCallback(
    (direction: 1 | -1) => {
      if (searchMatches.length === 0) return
      const nextIdx = (searchMatchIdx + direction + searchMatches.length) % searchMatches.length
      setSearchMatchIdx(nextIdx)
      const node = searchMatches[nextIdx] as AnyNode
      setSelectedNode(searchMatches[nextIdx])
      if (fgRef.current) {
        const distance = 60
        const distRatio = 1 + distance / Math.hypot(node.x || 1, node.y || 1, node.z || 1)
        fgRef.current.cameraPosition(
          { x: (node.x || 0) * distRatio, y: (node.y || 0) * distRatio, z: (node.z || 0) * distRatio },
          { x: node.x || 0, y: node.y || 0, z: node.z || 0 },
          1000,
        )
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

  // P2-11: 연결 노드 클릭 시 해당 노드로 카메라 이동
  const handleConnectionClick = useCallback(
    (nodeId: string) => {
      const target = filteredData.nodes.find(n => n.id === nodeId) as AnyNode | undefined
      if (!target || !fgRef.current) return
      setSelectedNode(target)
      const distance = 60
      const distRatio = 1 + distance / Math.hypot(target.x || 1, target.y || 1, target.z || 1)
      fgRef.current.cameraPosition(
        { x: (target.x || 0) * distRatio, y: (target.y || 0) * distRatio, z: (target.z || 0) * distRatio },
        { x: target.x || 0, y: target.y || 0, z: target.z || 0 },
        1000,
      )
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
              onChange={e => {
                setSearchQuery(e.target.value)
                if (!e.target.value.trim()) handleSearch('')
              }}
              onKeyDown={e => {
                if (e.key === 'Enter') {
                  if (searchMatches.length > 0 && searchQuery.trim()) {
                    navigateSearchMatch(1)
                  } else {
                    handleSearch(searchQuery)
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
                  handleSearch('')
                }
              }}
            />
            {searchMatches.length > 0 && (
              <span className="search-match-count">
                {searchMatchIdx + 1}/{searchMatches.length}
              </span>
            )}
          </div>
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

      {/* 3D 포스 그래프 */}
      {!loading && !isEmptyGraph && (
        <ForceGraph3D
          ref={fgRef}
          graphData={filteredData}
          nodeThreeObject={nodeThreeObject}
          nodeThreeObjectExtend={false}
          linkColor={(link: GraphLink) =>
            highlightLinks.has(getLinkKey(link))
              ? (bgColor === '#1a1a1a' ? 'rgba(255,255,255,0.8)' : 'rgba(0,0,0,0.6)')
              : (bgColor === '#1a1a1a' ? 'rgba(255,255,255,0.12)' : 'rgba(0,0,0,0.08)')
          }
          linkWidth={(link: GraphLink) => (highlightLinks.has(getLinkKey(link)) ? 1.5 : 0.3)}
          linkDirectionalArrowLength={3}
          linkDirectionalArrowRelPos={1}
          linkDirectionalParticles={(link: GraphLink) =>
            highlightLinks.has(getLinkKey(link)) ? 3 : 0
          }
          linkDirectionalParticleWidth={1.5}
          linkDirectionalParticleSpeed={0.006}
          backgroundColor={bgColor}
          onNodeClick={handleNodeClick}
          onNodeHover={handleNodeHover}
          onBackgroundClick={handleBackgroundClick}
          cooldownTicks={100}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 100)}
        />
      )}

      {/* 범례 */}
      {!loading && nodeTypes.length > 0 && (
        <div className="graph-legend">
          <h4>노드 유형</h4>
          <div className="legend-items">
            {nodeTypes.map(type => (
              <button
                key={type}
                className={`legend-item ${hiddenTypes.has(type) ? 'legend-item-hidden' : ''}`}
                onClick={() => toggleType(type)}
                aria-pressed={!hiddenTypes.has(type)}
                aria-label={`${toKo(type, NODE_TYPE_KO)} 노드 필터`}
              >
                <span
                  className="legend-dot"
                  style={{
                    backgroundColor: hiddenTypes.has(type)
                      ? '#444'
                      : NODE_COLORS[type] || NODE_COLORS['default'],
                  }}
                />
                <span className="legend-label">{toKo(type, NODE_TYPE_KO)}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* 선택된 노드 상세 패널 */}
      {selectedNode && (
        <div className="node-info-panel">
          <div className="node-info-header">
            <span
              className="node-type-badge"
              style={{ backgroundColor: selectedNode.color }}
            >
              {toKo(selectedNode.label, NODE_TYPE_KO)}
            </span>
            <button className="close-btn" onClick={() => setSelectedNode(null)} aria-label="패널 닫기">
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
              <h4>연결 ({selectedConnections.length})</h4>
              <ul>
                {selectedConnections.slice(0, 10).map((conn, i) => (
                  <li
                    key={i}
                    className="conn-clickable"
                    role="button"
                    tabIndex={0}
                    onClick={() => handleConnectionClick(conn.id)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); handleConnectionClick(conn.id) } }}
                  >
                    <span className="conn-dot" style={{ backgroundColor: conn.color }} />
                    <span className="conn-type">{toKo(conn.type, LINK_TYPE_KO)}</span>
                    <span className="conn-name">{conn.name}</span>
                  </li>
                ))}
                {selectedConnections.length > 10 && (
                  <li className="conn-more">+{selectedConnections.length - 10}개 더</li>
                )}
              </ul>
            </div>
          )}

          {/* P2-11: 관련 메모리 */}
          <div className="node-memories">
            <h4>관련 메모리</h4>
            {isLoadingMemories && <p className="memories-loading">불러오는 중...</p>}
            {!isLoadingMemories && relatedMemories.length === 0 && (
              <p className="memories-empty">관련 메모리가 없습니다</p>
            )}
            {!isLoadingMemories && relatedMemories.length > 0 && (
              <ul>
                {relatedMemories.map(m => (
                  <li
                    key={m.id}
                    className="memory-item"
                    role="button"
                    tabIndex={0}
                    onClick={() => setSelectedMemoryId(m.id)}
                    onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); setSelectedMemoryId(m.id) } }}
                  >
                    <BookOpen size={14} className="memory-icon" />
                    <span className="memory-title">{m.title || m.content?.substring(0, 40) || '메모리'}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <button
            className="chat-with-topic-btn"
            onClick={() => handleStartChat(selectedNode)}
          >
            이 주제로 대화하기
          </button>
        </div>
      )}

      {/* 조작 안내 */}
      {!loading && !isEmptyGraph && (
        <div className="graph-controls">
          <span>드래그: 회전</span>
          <span>스크롤: 확대/축소</span>
          <span>클릭: 포커스</span>
          <span>우클릭 드래그: 이동</span>
        </div>
      )}

      {/* P2-11: 메모리 상세 모달 */}
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
