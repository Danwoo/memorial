import { useState } from 'react'
import { useToast } from '../contexts/ToastContext'
import type { SearchResult } from '../types'
import { searchMemories } from '../api'

export function useMemorySearch() {
  const toast = useToast()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<SearchResult[]>([])
  const [isSearching, setIsSearching] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [showFilters, setShowFilters] = useState(false)
  const [sourceFilter, setSourceFilter] = useState<string>('')
  const [daysFilter, setDaysFilter] = useState<string>('')

  const handleSearch = async () => {
    if (!query.trim()) return
    setIsSearching(true)
    setHasSearched(true)
    try {
      const data = await searchMemories({
        q: query,
        source_type: sourceFilter || undefined,
        days: daysFilter || undefined,
      })
      setResults(data.results || [])
    } catch (error) {
      console.error('검색 실패:', error)
      toast.error('검색에 실패했습니다.')
      setResults([])
    } finally {
      setIsSearching(false)
    }
  }

  const clearFilters = () => {
    setSourceFilter('')
    setDaysFilter('')
  }

  return {
    query,
    setQuery,
    results,
    isSearching,
    hasSearched,
    showFilters,
    setShowFilters,
    sourceFilter,
    setSourceFilter,
    daysFilter,
    setDaysFilter,
    handleSearch,
    clearFilters,
    hasFilters: !!(sourceFilter || daysFilter),
  }
}
