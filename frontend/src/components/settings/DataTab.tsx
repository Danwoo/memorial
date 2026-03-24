interface DataTabProps {
  canInstall: boolean
  isInstalled: boolean
  handleOnboardingReset: () => void
  handleInstallPWA: () => Promise<void>
}

export default function DataTab({
  canInstall,
  isInstalled,
  handleOnboardingReset,
  handleInstallPWA,
}: DataTabProps) {
  return (
    <div className="settings-tab-content">
      <div className="settings-card">
        <div className="setting-row" style={{ borderTop: 'none' }}>
          <div className="setting-info">
            <span className="setting-label">온보딩 다시 보기</span>
            <span className="setting-desc">제품 소개 가이드를 다시 확인합니다</span>
          </div>
          <button className="btn btn-sm btn-secondary" onClick={handleOnboardingReset} type="button">
            다시 보기
          </button>
        </div>

        {(canInstall || isInstalled) && (
          <div className="setting-row">
            <div className="setting-info">
              <span className="setting-label">앱 설치하기</span>
              <span className="setting-desc">홈 화면에 추가하여 앱처럼 사용</span>
            </div>
            {isInstalled ? (
              <span className="status-badge connected">설치됨</span>
            ) : (
              <button className="btn btn-sm btn-primary" onClick={handleInstallPWA} type="button">
                설치
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
