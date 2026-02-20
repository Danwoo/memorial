import type { ExportCounts } from '../../api/export'

interface DataTabProps {
  exportCounts: ExportCounts | null
  exportLoading: string | null
  canInstall: boolean
  isInstalled: boolean
  handleExport: (type: 'memories' | 'journals' | 'all') => Promise<void>
  handleOnboardingReset: () => void
  handleInstallPWA: () => Promise<void>
}

export default function DataTab({
  exportCounts,
  exportLoading,
  canInstall,
  isInstalled,
  handleExport,
  handleOnboardingReset,
  handleInstallPWA,
}: DataTabProps) {
  return (
    <div className="settings-tab-content">
      <div className="settings-card">
        <h3 className="card-title">데이터 내보내기</h3>
        {exportCounts && (
          <p className="setting-desc" style={{ marginBottom: 'var(--space-md)' }}>
            기억 {exportCounts.memories}개, 저널 {exportCounts.journals}개
          </p>
        )}
        <div className="export-buttons">
          <button className="btn btn-sm btn-secondary" onClick={() => handleExport('memories')} disabled={exportLoading !== null}>
            {exportLoading === 'memories' ? '준비 중...' : '기억 (JSON)'}
          </button>
          <button className="btn btn-sm btn-secondary" onClick={() => handleExport('journals')} disabled={exportLoading !== null}>
            {exportLoading === 'journals' ? '준비 중...' : '저널 (Markdown)'}
          </button>
          <button className="btn btn-sm btn-secondary" onClick={() => handleExport('all')} disabled={exportLoading !== null}>
            {exportLoading === 'all' ? '준비 중...' : '전체 백업 (JSON)'}
          </button>
        </div>
      </div>

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
