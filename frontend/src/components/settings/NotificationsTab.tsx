import type { NudgeSetting } from '../../api/notifications'

interface NotificationsTabProps {
  pushSupported: boolean
  pushSubscribed: boolean
  pushLoading: boolean
  nudgeSettings: NudgeSetting[]
  nudgeLoading: boolean
  handlePushSubscribe: () => Promise<void>
  handleNudgeToggle: (nudgeType: string, enabled: boolean) => Promise<void>
  handleNudgeHourChange: (nudgeType: string, hour: number) => Promise<void>
}

// 넛지 타입별 설정값 조회 헬퍼
function getNudgeSetting(nudgeSettings: NudgeSetting[], type: string) {
  return nudgeSettings.find((n) => n.nudge_type === type)
}

export default function NotificationsTab({
  pushSupported,
  pushSubscribed,
  pushLoading,
  nudgeSettings,
  nudgeLoading,
  handlePushSubscribe,
  handleNudgeToggle,
  handleNudgeHourChange,
}: NotificationsTabProps) {
  return (
    <div className="settings-tab-content">
      <div className="settings-card">
        {/* 브라우저 푸시 권한 */}
        <div className="setting-row">
          <div className="setting-info">
            <span className="setting-label">브라우저 알림</span>
            <span className="setting-desc">푸시 알림을 받으려면 브라우저 권한이 필요합니다</span>
          </div>
          {!pushSupported ? (
            <span className="status-badge">미지원</span>
          ) : pushSubscribed ? (
            <span className="status-badge connected">활성화됨</span>
          ) : (
            <button className="btn btn-sm btn-primary" onClick={handlePushSubscribe} disabled={pushLoading}>
              {pushLoading ? '처리 중...' : '알림 허용'}
            </button>
          )}
        </div>

        <div className="setting-row">
          <div className="setting-info">
            <span className="setting-label">저녁 회고</span>
            <span className="setting-desc">오늘 저장한 기억 수와 주요 토픽을 알려줍니다</span>
          </div>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={getNudgeSetting(nudgeSettings, 'evening_review')?.enabled ?? true}
              onChange={(e) => handleNudgeToggle('evening_review', e.target.checked)}
              disabled={nudgeLoading}
            />
            <span className="toggle-slider" />
          </label>
        </div>

        {getNudgeSetting(nudgeSettings, 'evening_review')?.enabled && (
          <div className="setting-row setting-sub">
            <span className="setting-label">발송 시간</span>
            <select
              value={getNudgeSetting(nudgeSettings, 'evening_review')?.delivery_hour ?? 21}
              onChange={(e) => handleNudgeHourChange('evening_review', Number(e.target.value))}
              disabled={nudgeLoading}
            >
              {Array.from({ length: 5 }, (_, i) => i + 19).map((h) => (
                <option key={h} value={h}>{String(h).padStart(2, '0')}:00</option>
              ))}
            </select>
          </div>
        )}

        <div className="setting-row">
          <div className="setting-info">
            <span className="setting-label">주간 요약</span>
            <span className="setting-desc">매주 일요일에 이번 주 활동 통계를 보내줍니다</span>
          </div>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={getNudgeSetting(nudgeSettings, 'weekly_summary')?.enabled ?? true}
              onChange={(e) => handleNudgeToggle('weekly_summary', e.target.checked)}
              disabled={nudgeLoading}
            />
            <span className="toggle-slider" />
          </label>
        </div>

        <div className="setting-row">
          <div className="setting-info">
            <span className="setting-label">기억 연결 발견</span>
            <span className="setting-desc">저장한 기억들 사이의 연결을 찾아 알려줍니다</span>
          </div>
          <label className="toggle-switch">
            <input
              type="checkbox"
              checked={getNudgeSetting(nudgeSettings, 'connection_found')?.enabled ?? true}
              onChange={(e) => handleNudgeToggle('connection_found', e.target.checked)}
              disabled={nudgeLoading}
            />
            <span className="toggle-slider" />
          </label>
        </div>
      </div>
    </div>
  )
}
