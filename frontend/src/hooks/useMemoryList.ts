import { useState, useCallback } from 'react'
import { useToast } from '../contexts/ToastContext'
import type { Memory } from '../types'
import type { MemoryListParams } from '../api/memories'
import { fetchMemories } from '../api'

export function useMemoryList() {
  const toast = useToast()
  const [memories, setMemories] = useState<Memory[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [sortBy, setSortBy] = useState<'created_at' | 'updated_at' | 'title'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [sourceFilter, setSourceFilter] = useState<string>('')

  const loadMemories = useCallback(async () => {
    setIsLoading(true)
    try {
      const params: MemoryListParams = {
        limit: 100,
        sort_by: sortBy,
        sort_order: sortOrder,
      }
      if (sourceFilter) params.source_type = sourceFilter
      const data = await fetchMemories(params)
      setMemories(data.items || [])
    } catch (error) {
      console.error('메모리 목록 로드 실패:', error)
      toast.error('메모리 목록을 불러오지 못했습니다.')
    } finally {
      setIsLoading(false)
    }
  }, [toast, sortBy, sortOrder, sourceFilter])

  return {
    memories,
    isLoading,
    loadMemories,
    sortBy,
    setSortBy,
    sortOrder,
    setSortOrder,
    sourceFilter,
    setSourceFilter,
  }
}
