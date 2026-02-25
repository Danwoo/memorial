import { Flame, Trophy, Calendar } from 'lucide-react'
import type { StreakData } from '../../types'

function getStreakMessage(streak: number): string {
  if (streak === 0) return '오늘 기록을 시작해보세요!'
  if (streak === 1) return '첫 걸음을 내딛었어요!'
  if (streak < 3) return '좋은 시작이에요!'
  if (streak < 7) return '습관이 만들어지고 있어요!'
  if (streak < 14) return '꾸준함이 빛나고 있어요!'
  if (streak < 30) return '대단해요! 2주 이상 연속!'
  return '한 달 넘는 연속 기록!'
}

interface StreakCardProps {
  streak: StreakData
}

export default function StreakCard({ streak }: StreakCardProps) {
  return (
    <div className="streak-card">
      <div className="streak-main">
        <Flame size={32} className="streak-icon" />
        <div className="streak-number">{streak.current_streak}</div>
        <div className="streak-unit">일 연속</div>
      </div>
      <p className="streak-message">{getStreakMessage(streak.current_streak)}</p>
      <div className="streak-stats">
        <div className="streak-stat">
          <Trophy size={16} />
          <span>최장 {streak.longest_streak}일</span>
        </div>
        <div className="streak-stat">
          <Calendar size={16} />
          <span>총 {streak.total_active_days}일 활동</span>
        </div>
      </div>
    </div>
  )
}
