import { Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useIsMobile } from '../hooks/useMediaQuery'
import { useDemoMode } from '../contexts/DemoContext'
import { useSocratesChat } from '../hooks/useSocratesChat'
import SocratesPanel from './socrates/SocratesPanel'
import FeatureTip from './FeatureTip'
import './SocratesView.css'

export default function SocratesView() {
  const navigate = useNavigate()
  const { isDemoMode: isDemo } = useDemoMode()
  const pathPrefix = isDemo ? '/demo' : ''
  const isMobile = useIsMobile()
  const chat = useSocratesChat({ mode: 'standalone', agentType: 'oracle' })

  return (
    <div className="socrates-view">
      <FeatureTip
        tipKey="socrates-intro"
        message="AI 대화 상대와 하루를 돌아보세요. 다이어리 작성 전 Evening 모드를 먼저 시도해보세요."
      />
      <div className="socrates-header">
        <div>
          <h1>AI 대화</h1>
          <p className="socrates-subtitle">AI와 함께 하루를 돌아보세요</p>
        </div>
        {isMobile && (
          <button
            className="socrates-new-btn"
            onClick={() => navigate(`${pathPrefix}/chat`, { state: { newSession: true } })}
            type="button"
            aria-label="새 대화"
          >
            <Plus size={20} />
          </button>
        )}
      </div>
      <SocratesPanel chat={chat} />
    </div>
  )
}
