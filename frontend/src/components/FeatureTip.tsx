import { useState, useEffect } from 'react'
import { X, Lightbulb } from 'lucide-react'
import './FeatureTip.css'

interface FeatureTipProps {
  tipKey: string
  message: string
}

export default function FeatureTip({ tipKey, message }: FeatureTipProps) {
  const storageKey = `memoir:tip-dismissed:${tipKey}`
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    if (!localStorage.getItem(storageKey)) {
      setVisible(true)
    }
  }, [storageKey])

  const dismiss = () => {
    localStorage.setItem(storageKey, '1')
    setVisible(false)
  }

  if (!visible) return null

  return (
    <div className="feature-tip" role="note">
      <Lightbulb size={14} className="feature-tip__icon" />
      <span className="feature-tip__message">{message}</span>
      <button
        className="feature-tip__close"
        onClick={dismiss}
        type="button"
        aria-label="팁 닫기"
      >
        <X size={12} />
      </button>
    </div>
  )
}
