import { Flame } from 'lucide-react'
import type { StreakData } from '../../types'
import './StreakBadge.css'

interface StreakBadgeProps {
  streak: StreakData
}

export default function StreakBadge({ streak }: StreakBadgeProps) {
  if (streak.current_streak <= 0) return null

  return (
    <span className="streak-badge" title={`최장 ${streak.longest_streak}일 | 총 ${streak.total_active_days}일 활동`}>
      <Flame size={16} className="streak-badge__icon" />
      <span className="streak-badge__count">{streak.current_streak}</span>
      <span className="streak-badge__label">일 연속</span>
    </span>
  )
}
