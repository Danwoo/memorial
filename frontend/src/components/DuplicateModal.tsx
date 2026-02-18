import { useState, useEffect } from 'react'
import { X, Loader2, Merge, SkipForward } from 'lucide-react'
import { useToast } from '../contexts/ToastContext'
import { fetchDuplicates, mergeMemories } from '../api/duplicates'
import type { DuplicatePair } from '../api/duplicates'
import './DuplicateModal.css'

interface DuplicateModalProps {
  onClose: () => void
  onMerged: () => void
}

export default function DuplicateModal({ onClose, onMerged }: DuplicateModalProps) {
  const toast = useToast()
  const [loading, setLoading] = useState(true)
  const [pairs, setPairs] = useState<DuplicatePair[]>([])
  const [merging, setMerging] = useState<string | null>(null)
  const [dismissed, setDismissed] = useState<Set<string>>(new Set())

  useEffect(() => {
    fetchDuplicates()
      .then(res => setPairs(res.pairs))
      .catch(() => toast.error('중복 감지에 실패했습니다'))
      .finally(() => setLoading(false))
  }, [toast])

  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [onClose])

  const handleMerge = async (keepId: string, mergeId: string, pairKey: string) => {
    setMerging(pairKey)
    try {
      await mergeMemories(keepId, mergeId)
      toast.success('메모리가 병합되었습니다')
      setDismissed(prev => new Set(prev).add(pairKey))
      onMerged()
    } catch {
      toast.error('병합에 실패했습니다')
    } finally {
      setMerging(null)
    }
  }

  const handleDismiss = (pairKey: string) => {
    setDismissed(prev => new Set(prev).add(pairKey))
  }

  const visiblePairs = pairs.filter(p => {
    const key = `${p.memory_a.id}-${p.memory_b.id}`
    return !dismissed.has(key)
  })

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content duplicate-modal card" role="dialog" aria-modal="true" aria-label="중복 메모리 정리" onClick={e => e.stopPropagation()}>
        <div className="duplicate-modal-header">
          <h2>중복 메모리 정리</h2>
          <button className="btn btn-ghost" onClick={onClose}><X size={18} /></button>
        </div>

        {loading ? (
          <div className="duplicate-loading">
            <Loader2 size={24} className="spinning" />
            <p>중복 항목을 분석하고 있습니다...</p>
          </div>
        ) : visiblePairs.length === 0 ? (
          <div className="duplicate-empty">
            <p>중복 메모리가 없습니다.</p>
          </div>
        ) : (
          <div className="duplicate-list">
            <p className="duplicate-count">{visiblePairs.length}개 중복 발견</p>
            {visiblePairs.map(pair => {
              const pairKey = `${pair.memory_a.id}-${pair.memory_b.id}`
              const isMerging = merging === pairKey
              return (
                <div key={pairKey} className="duplicate-pair">
                  <div className="duplicate-card">
                    <h4>{pair.memory_a.title}</h4>
                    {pair.memory_a.summary && <p>{pair.memory_a.summary}</p>}
                    <span className="duplicate-source">{pair.memory_a.source_type}</span>
                  </div>
                  <div className="duplicate-similarity">
                    <span className="similarity-pct">{Math.round(pair.similarity * 100)}%</span>
                    <span className="similarity-reason">{pair.reason}</span>
                    <div className="duplicate-actions">
                      <button
                        className="btn btn-primary btn-sm"
                        onClick={() => handleMerge(pair.memory_a.id, pair.memory_b.id, pairKey)}
                        disabled={isMerging}
                      >
                        <Merge size={14} /> {isMerging ? '병합 중...' : '병합'}
                      </button>
                      <button
                        className="btn btn-secondary btn-sm"
                        onClick={() => handleDismiss(pairKey)}
                        disabled={isMerging}
                      >
                        <SkipForward size={14} /> 무시
                      </button>
                    </div>
                  </div>
                  <div className="duplicate-card">
                    <h4>{pair.memory_b.title}</h4>
                    {pair.memory_b.summary && <p>{pair.memory_b.summary}</p>}
                    <span className="duplicate-source">{pair.memory_b.source_type}</span>
                  </div>
                </div>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
