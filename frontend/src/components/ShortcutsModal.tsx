import { useEffect } from 'react'
import { X } from 'lucide-react'
import { useFocusTrap } from '../hooks/useFocusTrap'
import './ShortcutsModal.css'

interface ShortcutsModalProps {
  onClose: () => void
}

const SHORTCUTS = [
  { section: '전역', items: [
    { keys: ['Ctrl', 'K'], desc: '검색 팔레트 열기' },
    { keys: ['?'],         desc: '단축키 목록 보기' },
    { keys: ['Esc'],       desc: '현재 팝업 닫기' },
  ]},
  { section: '다이어리', items: [
    { keys: ['Ctrl', 'S'],  desc: '저장' },
    { keys: ['Ctrl', '['],  desc: '이전 날짜로' },
    { keys: ['Ctrl', ']'],  desc: '다음 날짜로' },
  ]},
  { section: '검색 결과', items: [
    { keys: ['↑', '↓'],        desc: '항목 이동' },
    { keys: ['Tab'],            desc: '다음 항목' },
    { keys: ['Shift', 'Tab'],   desc: '이전 항목' },
    { keys: ['Enter'],          desc: '선택' },
  ]},
]

export default function ShortcutsModal({ onClose }: ShortcutsModalProps) {
  const trapRef = useFocusTrap()

  useEffect(() => {
    const handler = (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  return (
    <div className="shortcuts-overlay" onClick={onClose} role="presentation">
      <div
        className="shortcuts-modal"
        role="dialog"
        aria-modal="true"
        aria-label="키보드 단축키"
        onClick={(e) => e.stopPropagation()}
        ref={trapRef}
      >
        <div className="shortcuts-header">
          <h2>키보드 단축키</h2>
          <button className="shortcuts-close" onClick={onClose} aria-label="닫기" type="button">
            <X size={18} />
          </button>
        </div>
        <div className="shortcuts-body">
          {SHORTCUTS.map(({ section, items }) => (
            <div key={section} className="shortcuts-section">
              <h3 className="shortcuts-section-title">{section}</h3>
              <dl className="shortcuts-list">
                {items.map(({ keys, desc }) => (
                  <div key={desc} className="shortcuts-row">
                    <dt className="shortcuts-keys">
                      {keys.map((k, i) => (
                        <span key={i}>
                          <kbd>{k}</kbd>
                          {i < keys.length - 1 && <span className="shortcuts-plus">+</span>}
                        </span>
                      ))}
                    </dt>
                    <dd className="shortcuts-desc">{desc}</dd>
                  </div>
                ))}
              </dl>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
