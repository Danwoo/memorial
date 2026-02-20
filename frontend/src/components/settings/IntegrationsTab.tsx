import type { ProviderInfo, BotSettings, BotSettingsUpdate, ChannelLinkCode, ChannelStatus } from '../../api/integrations'

const PROVIDER_LABELS: Record<string, string> = {
  google: 'Google',
  kakao: 'Kakao',
}

const SUPPORTED_PROVIDERS = ['google', 'kakao'] as const

const KAKAO_CHANNEL_CHAT_URL = 'https://pf.kakao.com/_NxoGzX/chat'

interface IntegrationsTabProps {
  loading: boolean
  providers: ProviderInfo[]
  actionLoading: string | null
  botSettings: BotSettings | null
  botLoading: boolean
  channelStatus: ChannelStatus | null
  channelLoading: boolean
  linkCode: ChannelLinkCode | null
  countdown: string
  kakaoLinked: boolean
  isProviderLinked: (provider: string) => boolean
  getProviderIdentity: (provider: string) => ProviderInfo | undefined
  handleLink: (provider: 'google' | 'kakao') => Promise<void>
  handleUnlink: (provider: string) => Promise<void>
  handleBotSettingChange: (update: BotSettingsUpdate) => Promise<void>
  handleGenerateLinkCode: () => Promise<void>
  handleDisconnectChannel: () => Promise<void>
  onCopyLinkCode: (code: string) => void
}

export default function IntegrationsTab({
  loading,
  providers,
  actionLoading,
  botSettings,
  botLoading,
  channelStatus,
  channelLoading,
  linkCode,
  countdown,
  kakaoLinked,
  isProviderLinked,
  getProviderIdentity,
  handleLink,
  handleUnlink,
  handleBotSettingChange,
  handleGenerateLinkCode,
  handleDisconnectChannel,
  onCopyLinkCode,
}: IntegrationsTabProps) {
  return (
    <div className="settings-tab-content">
      {/* 연결된 계정 */}
      <h3 className="tab-section-title">연결된 계정</h3>
      <div className="settings-card">
        {loading ? (
          <div className="loading-spinner small" />
        ) : (
          SUPPORTED_PROVIDERS.map((provider) => {
            const linked = isProviderLinked(provider)
            const isOnlyProvider = providers.length <= 1 && linked
            const isActioning = actionLoading === provider
            return (
              <div key={provider} className="setting-row integration-row">
                <div className="integration-left">
                  <div className={`provider-icon ${provider}-icon`}>
                    {provider === 'google' && (
                      <svg viewBox="0 0 24 24" width="20" height="20">
                        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 01-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z"/>
                        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                      </svg>
                    )}
                    {provider === 'kakao' && (
                      <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                        <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
                      </svg>
                    )}
                  </div>
                  <div className="integration-info">
                    <span className="setting-label">{PROVIDER_LABELS[provider]}</span>
                    <span className="setting-desc">
                      {linked ? (getProviderIdentity(provider)?.email ?? '연결됨') : '연결되지 않음'}
                    </span>
                  </div>
                </div>
                <div className="integration-actions">
                  {linked ? (
                    <>
                      <span className="status-badge connected">연결됨</span>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleUnlink(provider)}
                        disabled={isOnlyProvider || isActioning}
                        title={isOnlyProvider ? '최소 1개의 로그인 방식이 필요합니다' : undefined}
                      >
                        {isActioning ? '...' : '해제'}
                      </button>
                    </>
                  ) : (
                    <button
                      className={`btn btn-sm ${provider}-connect-btn`}
                      onClick={() => handleLink(provider)}
                      disabled={isActioning}
                    >
                      {isActioning ? '...' : '연결'}
                    </button>
                  )}
                </div>
              </div>
            )
          })
        )}
      </div>

      {/* 카카오톡 채널 */}
      <h3 className="tab-section-title">카카오톡 채널</h3>
      <div className="settings-card">
        <div className="channel-header">
          <div className="integration-left">
            <div className="provider-icon kakao-icon">
              <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                <path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/>
              </svg>
            </div>
            <div className="integration-info">
              <span className="setting-label">채널 연결</span>
              <span className="setting-desc">카카오톡에서 URL이나 메모를 보내 바로 저장</span>
            </div>
          </div>
          {channelStatus?.connected && (
            <div className="integration-actions">
              <span className="status-badge connected">연결됨</span>
              <button className="btn btn-secondary btn-sm" onClick={handleDisconnectChannel} disabled={channelLoading}>
                {channelLoading ? '...' : '해제'}
              </button>
            </div>
          )}
        </div>

        {!channelStatus?.connected && (
          <div className="channel-connect-section">
            {linkCode ? (
              <div className="channel-link-steps">
                <div className="link-step">
                  <span className="link-step-number">1</span>
                  <div className="link-step-content">
                    <span className="link-step-label">연결 코드 복사 완료</span>
                    <div className="link-code-command"
                      onClick={() => onCopyLinkCode(linkCode.code)}
                      title="클릭하여 다시 복사"
                    >
                      #연결 {linkCode.code}
                    </div>
                  </div>
                </div>
                <div className="link-step">
                  <span className="link-step-number">2</span>
                  <div className="link-step-content">
                    <span className="link-step-label">카카오톡에서 붙여넣기</span>
                    <a href={KAKAO_CHANNEL_CHAT_URL} target="_blank" rel="noopener noreferrer"
                      className="btn kakao-connect-btn btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', textDecoration: 'none', marginTop: '4px' }}>
                      <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/></svg>
                      채널 열기
                    </a>
                  </div>
                </div>
                <span className="link-code-timer">남은 시간: {countdown}</span>
              </div>
            ) : (
              <div className="channel-connect-cta">
                <p className="setting-desc">카카오톡 Memoir 채널에 아무 메시지를 보내면 자동 연결 링크를 받을 수 있습니다.</p>
                <div className="channel-connect-buttons">
                  <a href={KAKAO_CHANNEL_CHAT_URL} target="_blank" rel="noopener noreferrer"
                    className="btn kakao-connect-btn btn-sm" style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', textDecoration: 'none' }}>
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M12 3C6.477 3 2 6.463 2 10.691c0 2.724 1.8 5.113 4.508 6.458-.199.748-.72 2.713-.826 3.132-.13.525.192.518.405.377.167-.11 2.665-1.81 3.747-2.545.7.1 1.42.152 2.166.152 5.523 0 10-3.463 10-7.574C22 6.463 17.523 3 12 3z"/></svg>
                    카카오톡에서 연결
                  </a>
                  <button className="btn btn-secondary btn-sm" onClick={handleGenerateLinkCode} disabled={channelLoading}>
                    {channelLoading ? '생성 중...' : '코드로 연결'}
                  </button>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* 카카오톡 다이제스트 */}
      <div className="settings-card">
        <div className="setting-row" style={{ borderTop: 'none' }}>
          <div className="setting-info">
            <span className="setting-label">일일 다이제스트</span>
            <span className="setting-desc">매일 정해진 시간에 오늘의 기록을 카카오톡으로 전송</span>
          </div>
          {!kakaoLinked ? (
            <span className="status-badge">카카오 연결 필요</span>
          ) : (
            <label className="toggle-switch">
              <input
                type="checkbox"
                checked={botSettings?.enabled ?? false}
                onChange={(e) => handleBotSettingChange({ enabled: e.target.checked })}
                disabled={botLoading}
              />
              <span className="toggle-slider" />
            </label>
          )}
        </div>

        {kakaoLinked && botSettings?.enabled && (
          <>
            <div className="setting-row setting-sub">
              <span className="setting-label">발송 시간</span>
              <select
                value={botSettings?.delivery_hour ?? 21}
                onChange={(e) => handleBotSettingChange({ delivery_hour: Number(e.target.value) })}
                disabled={botLoading}
              >
                {Array.from({ length: 24 }, (_, i) => (
                  <option key={i} value={i}>{String(i).padStart(2, '0')}:00</option>
                ))}
              </select>
            </div>
            <div className="setting-row setting-sub">
              <span className="setting-label">포함 항목</span>
              <div className="bot-checkboxes">
                <label><input type="checkbox" checked={botSettings?.include_memories ?? true}
                  onChange={(e) => handleBotSettingChange({ include_memories: e.target.checked })} disabled={botLoading} /> 기억</label>
                <label><input type="checkbox" checked={botSettings?.include_journals ?? true}
                  onChange={(e) => handleBotSettingChange({ include_journals: e.target.checked })} disabled={botLoading} /> 일기</label>
                <label><input type="checkbox" checked={botSettings?.include_insights ?? true}
                  onChange={(e) => handleBotSettingChange({ include_insights: e.target.checked })} disabled={botLoading} /> 인사이트</label>
              </div>
            </div>
            {botSettings?.last_delivery && (
              <div className="setting-row setting-sub">
                <span className="setting-label">최근 발송</span>
                <span className={`delivery-status ${botSettings.last_delivery.status}`}>
                  {botSettings.last_delivery.status === 'success' && '발송 완료'}
                  {botSettings.last_delivery.status === 'failed' && '발송 실패'}
                  {botSettings.last_delivery.status === 'token_expired' && '토큰 만료'}
                  {botSettings.last_delivery.status === 'no_content' && '콘텐츠 없음'}
                  {' — '}
                  {new Date(botSettings.last_delivery.delivered_at).toLocaleString('ko-KR')}
                </span>
              </div>
            )}
          </>
        )}
      </div>

      {/* Chrome Extension */}
      <div className="settings-card">
        <div className="setting-row integration-row" style={{ borderTop: 'none' }}>
          <div className="integration-left">
            <div className="provider-icon chrome-icon">
              <svg viewBox="0 0 24 24" width="20" height="20">
                <circle cx="12" cy="12" r="10" fill="none" stroke="currentColor" strokeWidth="2"/>
                <circle cx="12" cy="12" r="4" fill="currentColor"/>
              </svg>
            </div>
            <div className="integration-info">
              <span className="setting-label">Chrome Extension</span>
              <span className="setting-desc">웹 브라우징 중 기억을 빠르게 저장</span>
            </div>
          </div>
          <a href="https://github.com/Danwoo/memorial/tree/main/extension" target="_blank" rel="noopener noreferrer"
            className="btn btn-sm btn-secondary" style={{ textDecoration: 'none' }}>
            설치 가이드
          </a>
        </div>
      </div>
    </div>
  )
}
