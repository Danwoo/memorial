import { Plus } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { useIsMobile } from '../hooks/useMediaQuery'
import { useDemoMode } from '../contexts/DemoContext'
import { useSocratesChat } from '../hooks/useSocratesChat'
import SocratesPanel from './socrates/SocratesPanel'
import './SocratesView.css'

export default function SocratesView() {
  const navigate = useNavigate()
  const { isDemoMode: isDemo } = useDemoMode()
  const pathPrefix = isDemo ? '/demo' : ''
  const isMobile = useIsMobile()
  const chat = useSocratesChat({ mode: 'standalone' })

  return (
    <div className="socrates-view">
      <div className="socrates-header">
        <div>
          <h1>Socrates</h1>
          <p className="socrates-subtitle">당신의 지적 동반자</p>
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
