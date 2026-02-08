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

/** Validation error detail from backend */
export interface ValidationErrorItem {
  loc: (string | number)[]
  msg: string
  type: string
}

/** Common API error shape (detail can be string or validation error array) */
export interface ApiError {
  error?: string
  detail: string | ValidationErrorItem[]
  status?: number
}
