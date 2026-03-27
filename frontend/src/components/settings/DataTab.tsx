import { useState } from 'react'
import { Download } from 'lucide-react'
import { exportScraps, exportDiaries, exportAll } from '../../api/export'
import { useToast } from '../../contexts/ToastContext'

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
  const toast = useToast()
  const [exportLoading, setExportLoading] = useState<string | null>(null)

  const handleExport = async (type: 'scraps' | 'diaries' | 'all') => {
    setExportLoading(type)
    try {
      if (type === 'scraps') await exportScraps()
      else if (type === 'diaries') await exportDiaries()
      else await exportAll()
      toast.success('내보내기가 완료되었습니다')
    } catch {
      toast.error('내보내기에 실패했습니다')
    } finally {
      setExportLoading(null)
    }
  }

  return (
    <div className="settings-tab-content">
      {/* 데이터 내보내기 */}
      <h3 className="tab-section-title">데이터 내보내기</h3>
      <div className="settings-card">
        <div className="setting-row" style={{ borderTop: 'none' }}>
          <div className="setting-info">
            <span className="setting-label">스크랩 내보내기</span>
            <span className="setting-desc">저장된 스크랩을 JSON으로 다운로드</span>
          </div>
          <button
            className="btn btn-sm btn-secondary"
            onClick={() => handleExport('scraps')}
            disabled={!!exportLoading}
            type="button"
          >
            <Download size={14} />
            {exportLoading === 'scraps' ? '...' : '내보내기'}
          </button>
        </div>
        <div className="setting-row">
          <div className="setting-info">
            <span className="setting-label">다이어리 내보내기</span>
            <span className="setting-desc">작성한 다이어리를 JSON으로 다운로드</span>
          </div>
          <button
            className="btn btn-sm btn-secondary"
            onClick={() => handleExport('diaries')}
            disabled={!!exportLoading}
            type="button"
          >
            <Download size={14} />
            {exportLoading === 'diaries' ? '...' : '내보내기'}
          </button>
        </div>
        <div className="setting-row">
          <div className="setting-info">
            <span className="setting-label">전체 데이터 내보내기</span>
            <span className="setting-desc">스크랩 + 다이어리 전체를 한번에 다운로드</span>
          </div>
          <button
            className="btn btn-sm btn-primary"
            onClick={() => handleExport('all')}
            disabled={!!exportLoading}
            type="button"
          >
            <Download size={14} />
            {exportLoading === 'all' ? '...' : '전체 내보내기'}
          </button>
        </div>
      </div>

      {/* 기타 */}
      <h3 className="tab-section-title">기타</h3>
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
