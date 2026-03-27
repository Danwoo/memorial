import { useState, useCallback, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'
import { useToast } from '../contexts/ToastContext'
import type { Scrap } from '../types'
import type { ScrapListParams } from '../api/scraps'
import { fetchScraps } from '../api'
import { getViewCache, setViewCache, CACHE_KEYS } from '../utils/viewCache'

const ITEMS_PER_PAGE = 20

export function useScrapList() {
  const { user } = useAuth()
  const userId = user?.id ?? ''
  const toast = useToast()
  const cached = userId ? getViewCache<Scrap[]>(userId, CACHE_KEYS.SCRAP_LIST) : null
  const [scraps, setScraps] = useState<Scrap[]>(cached ?? [])
  const [isLoading, setIsLoading] = useState(!cached)
  const [sortBy, setSortBy] = useState<'created_at' | 'updated_at' | 'title'>('created_at')
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc')
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [page, setPage] = useState(1)
  const [total, setTotal] = useState(0)
  const [searchQuery, setSearchQuery] = useState('')
  const [committedSearch, setCommittedSearch] = useState('')
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [tagFilter, setTagFilter] = useState<string[]>([])

  const totalPages = Math.max(1, Math.ceil(total / ITEMS_PER_PAGE))

  const loadScraps = useCallback(async () => {
    // 기본 상태(page=1, 검색 없음, 기본 정렬)에서만 캐시 사용
    const isDefault = page === 1 && !committedSearch && sortBy === 'created_at' && sortOrder === 'desc' && !sourceFilter && !dateFrom && !dateTo && tagFilter.length === 0
    if (isDefault && userId && getViewCache(userId, CACHE_KEYS.SCRAP_LIST)) {
      setIsLoading(false)
      return
    }

    setIsLoading(true)
    try {
      const params: ScrapListParams = {
        page,
        limit: ITEMS_PER_PAGE,
        sort_by: sortBy,
        sort_order: sortOrder,
      }
      if (sourceFilter) params.source_type = sourceFilter
      if (committedSearch) params.search = committedSearch
      if (dateFrom) params.date_from = dateFrom
      if (dateTo) params.date_to = dateTo
      if (tagFilter.length > 0) params.tags = tagFilter
      const data = await fetchScraps(params)
      const items = data.items || []
      setScraps(items)
      setTotal(data.total ?? 0)
      // 기본 상태일 때만 캐시 저장
      if (isDefault && userId) {
        setViewCache(userId, CACHE_KEYS.SCRAP_LIST, items)
      }
    } catch (error) {
      console.error('스크랩 목록 로드 실패:', error)
      toast.error('스크랩 목록을 불러오지 못했습니다.')
    } finally {
      setIsLoading(false)
    }
  }, [userId, toast, sortBy, sortOrder, sourceFilter, page, committedSearch, dateFrom, dateTo, tagFilter])

  const goToPage = useCallback((n: number) => {
    setPage(Math.max(1, Math.min(n, totalPages)))
  }, [totalPages])

  // 타이핑 시 300ms 디바운스 자동 검색
  useEffect(() => {
    const timer = setTimeout(() => {
      const trimmed = searchQuery.trim()
      if (trimmed !== committedSearch) {
        setCommittedSearch(trimmed)
        setPage(1)
      }
    }, 300)
    return () => clearTimeout(timer)
  }, [searchQuery]) // eslint-disable-line react-hooks/exhaustive-deps

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
    scraps,
    isLoading,
    loadScraps,
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
    dateFrom,
    setDateFrom,
    dateTo,
    setDateTo,
    tagFilter,
    setTagFilter,
  }
}
