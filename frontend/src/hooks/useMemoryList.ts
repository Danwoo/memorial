import { useState, useCallback } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import type { Memory } from '../types'
import type { MemoryListParams } from '../api/memories'
import { fetchMemories } from '../api'
import { getViewCache, setViewCache, CACHE_KEYS } from '../utils/viewCache'

const ITEMS_PER_PAGE = 20

export function useMemoryList() {
  const { user } = useAuth()
  const userId = user?.id ?? ''
  const toast = useToast()
  const cached = userId ? getViewCache<Memory[]>(userId, CACHE_KEYS.MEMORY_LIST) : null
  const [memories, setMemories] = useState<Memory[]>(cached ?? [])
  const [isLoading, setIsLoading] = useState(!cached)
  const [sortBy, setSortBy] = useState<'created_at' | 'updated_at' | 'title'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [committedSearch, setCommittedSearch] = useState('')

  const totalPages = Math.max(1, Math.ceil(total / ITEMS_PER_PAGE))

  const loadMemories = useCallback(async () => {
    // 기본 상태(page=1, 검색 없음, 기본 정렬)에서만 캐시 사용
    const isDefault = page === 1 && !committedSearch && sortBy === 'created_at' && sortOrder === 'desc' && !sourceFilter
    if (isDefault && userId && getViewCache(userId, CACHE_KEYS.MEMORY_LIST)) {
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    try {
      const params: MemoryListParams = {
        page,
        limit: ITEMS_PER_PAGE,
        sort_by: sortBy,
        sort_order: sortOrder,
      }
      if (sourceFilter) params.source_type = sourceFilter
      if (committedSearch) params.search = committedSearch
      const data = await fetchMemories(params)
      const items = data.items || []
      setMemories(items)
      setTotal(data.total ?? 0)
      // 기본 상태일 때만 캐시 저장
      if (isDefault && userId) {
        setViewCache(userId, CACHE_KEYS.MEMORY_LIST, items)
      }
    } catch (error) {
      console.error('메모리 목록 로드 실패:', error)
      toast.error('메모리 목록을 불러오지 못했습니다.')
    } finally {
      setIsLoading(false)
    }
  }, [userId, toast, sortBy, sortOrder, sourceFilter, page, committedSearch])

  const goToPage = useCallback((n: number) => {
    setPage(Math.max(1, Math.min(n, totalPages)))
  }, [totalPages])

  const commitSearch = useCallback(() => {
    setCommittedSearch(searchQuery.trim())
    setPage(1)
  }, [searchQuery])

  const clearSearch = useCallback(() => {
    setSearchQuery('')
    setCommittedSearch('')
    setPage(1)
  }, [])

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
    page,
    totalPages,
    total,
    searchQuery,
    setSearchQuery,
    commitSearch,
    clearSearch,
    goToPage,
  }
}
