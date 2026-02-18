import type { ReactNode } from 'react'
import './EmptyState.css'

interface Props {
  icon: ReactNode
  title: string
  description: string
  ctaLabel?: string
  onCtaClick?: () => void
}

export default function EmptyState({ icon, title, description, ctaLabel, onCtaClick }: Props) {
  return (
    <div className="empty-state-component">
      <div className="empty-state-icon">{icon}</div>
      <h3 className="empty-state-title">{title}</h3>
      <p className="empty-state-desc">{description}</p>
      {ctaLabel && onCtaClick && (
        <button className="empty-state-cta" onClick={onCtaClick}>
          {ctaLabel}
        </button>
      )}
    </div>
  )
}
