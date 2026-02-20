import { BookOpen } from 'lucide-react'
import type { GraphNode, SearchResult } from '../../types'
import { NODE_TYPE_KO, LINK_TYPE_KO, toKo } from './graphConstants'

interface ConnectionItem {
  id: string
  name: string
  label: string
  type: string
  color: string
}

interface NodeInfoPanelProps {
  node: GraphNode
  connections: ConnectionItem[]
  relatedMemories: SearchResult[]
  isLoadingMemories: boolean
  onClose: () => void
  onConnectionClick: (nodeId: string) => void
  onMemoryClick: (memoryId: string) => void
  onStartChat: (node: GraphNode) => void
  onViewMemories: () => void
}

export default function NodeInfoPanel({
  node,
  connections,
  relatedMemories,
  isLoadingMemories,
  onClose,
  onConnectionClick,
  onMemoryClick,
  onStartChat,
  onViewMemories,
}: NodeInfoPanelProps) {
  return (
    <div className="node-info-panel">
      <div className="node-info-header">
        <span
          className="node-type-badge"
          style={{ backgroundColor: node.color }}
        >
          {toKo(node.label, NODE_TYPE_KO)}
        </span>
        <button className="close-btn" onClick={onClose} aria-label="패널 닫기">
          &times;
        </button>
      </div>
      <h3>{node.name}</h3>
      <div className="node-meta">
        <span className="node-meta-item">연결 {connections.length}개</span>
        {node.properties?.source_type && (
          <span className="node-meta-item">{node.properties.source_type as string}</span>
        )}
        {node.properties?.created_at && (
          <span className="node-meta-item">{(node.properties.created_at as string).substring(0, 10)}</span>
        )}
      </div>

      {node.properties?.summary && (
        <p className="node-summary">{node.properties.summary as string}</p>
      )}

      {node.properties?.tags && (
        <div className="node-tags">
          {(node.properties.tags as string[]).map((tag: string, i: number) => (
            <span key={i} className="node-tag">
              #{tag}
            </span>
          ))}
        </div>
      )}

      {connections.length > 0 && (
        <div className="node-connections">
          <h4>연결 ({connections.length})</h4>
          <ul>
            {connections.slice(0, 10).map((conn, i) => (
              <li
                key={i}
                className="conn-clickable"
                role="button"
                tabIndex={0}
                onClick={() => onConnectionClick(conn.id)}
                onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onConnectionClick(conn.id) } }}
              >
                <span className="conn-dot" style={{ backgroundColor: conn.color }} />
                <span className="conn-type">{toKo(conn.type, LINK_TYPE_KO)}</span>
                <span className="conn-name">{conn.name}</span>
              </li>
            ))}
            {connections.length > 10 && (
              <li className="conn-more">+{connections.length - 10}개 더</li>
            )}
          </ul>
        </div>
      )}

      {/* 관련 메모리 */}
      <div className="node-memories">
        <h4>관련 메모리</h4>
        {isLoadingMemories && <p className="memories-loading">불러오는 중...</p>}
        {!isLoadingMemories && relatedMemories.length === 0 && (
          <p className="memories-empty">관련 메모리가 없습니다</p>
        )}
        {!isLoadingMemories && relatedMemories.length > 0 && (
          <>
            <ul>
              {relatedMemories.map(m => (
                <li
                  key={m.id}
                  className="memory-item"
                  role="button"
                  tabIndex={0}
                  onClick={() => onMemoryClick(m.id)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onMemoryClick(m.id) } }}
                >
                  <BookOpen size={14} className="memory-icon" />
                  <span className="memory-title">{m.title || m.content?.substring(0, 40) || '메모리'}</span>
                </li>
              ))}
            </ul>
            <button
              className="view-in-memories-link"
              onClick={onViewMemories}
            >
              기억 뷰에서 보기 →
            </button>
          </>
        )}
      </div>

      <button
        className="chat-with-topic-btn"
        onClick={() => onStartChat(node)}
      >
        이 주제로 대화하기
      </button>
    </div>
  )
}
