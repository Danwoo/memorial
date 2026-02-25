import { NODE_COLORS, NODE_TYPE_KO, toKo } from './mindmapConstants'

interface GraphLegendProps {
  nodeTypes: string[]
  hiddenTypes: Set<string>
  onToggleType: (type: string) => void
}

export default function GraphLegend({ nodeTypes, hiddenTypes, onToggleType }: GraphLegendProps) {
  return (
    <div className="mindmap-legend">
      <h4>노드 유형</h4>
      <div className="legend-items">
        {nodeTypes.map(type => (
          <button
            key={type}
            className={`legend-item ${hiddenTypes.has(type) ? 'legend-item-hidden' : ''}`}
            onClick={() => onToggleType(type)}
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
  )
}
