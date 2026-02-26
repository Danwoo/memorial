import { BookOpen } from 'lucide-react'
import type { MindmapNode, SearchResult } from '../../types'
import { NODE_TYPE_KO, LINK_TYPE_KO, toKo } from './mindmapConstants'

interface ConnectionItem {
  id: string
  name: string
  label: string
  type: string
  color: string
}

interface NodeInfoPanelProps {
  node: MindmapNode
  connections: ConnectionItem[]
  relatedScraps: SearchResult[]
  isLoadingScraps: boolean
  onClose: () => void
  onConnectionClick: (nodeId: string) => void
  onScrapClick: (memoryId: string) => void
  onStartChat: (node: MindmapNode) => void
  onViewScraps: () => void
}

export default function NodeInfoPanel({
  node,
  connections,
  relatedScraps,
  isLoadingScraps,
  onClose,
  onConnectionClick,
  onScrapClick,
  onStartChat,
  onViewScraps,
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

      {/* 관련 스크랩 */}
      <div className="node-scraps">
        <h4>관련 스크랩</h4>
        {isLoadingScraps && <p className="scraps-loading">불러오는 중...</p>}
        {!isLoadingScraps && relatedScraps.length === 0 && (
          <p className="scraps-empty">관련 스크랩가 없습니다</p>
        )}
        {!isLoadingScraps && relatedScraps.length > 0 && (
          <>
            <ul>
              {relatedScraps.map(m => (
                <li
                  key={m.id}
                  className="scrap-item"
                  role="button"
                  tabIndex={0}
                  onClick={() => onScrapClick(m.id)}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onScrapClick(m.id) } }}
                >
                  <BookOpen size={14} className="scrap-icon" />
                  <span className="scrap-title">{m.title || m.content?.substring(0, 40) || '스크랩'}</span>
                </li>
              ))}
            </ul>
            <button
              className="view-in-scraps-link"
              onClick={onViewScraps}
            >
              스크랩 뷰에서 보기 →
            </button>
          </>
        )}
      </div>

      <button
        className="socrates-with-topic-btn"
        onClick={() => onStartChat(node)}
      >
        이 주제로 대화하기
      </button>
    </div>
  )
}
