/** Common paginated list response wrapper */
export interface PaginatedResponse<T> {
  items: T[]
  total?: number
  page?: number
  limit?: number
  has_more?: boolean
}

/** Search results response */
export interface SearchResponse<T> {
  results: T[]
}

/** Related memories response */
export interface RelatedMemoriesResponse {
  memories: {
    id: string
    title: string
    summary: string
    type: string
    created_at: string
    similarity: number
  }[]
}

/** Common API error shape */
export interface ApiError {
  detail: string
  status?: number
}
