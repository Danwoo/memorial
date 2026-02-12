export type SourceType = 'WEB' | 'PDF' | 'NOTE' | 'KAKAO' | 'CHAT_HISTORY' | 'JOURNAL'

export interface Memory {
  id: string
  title: string
  summary: string | null
  source_type: SourceType
  created_at: string
  tags?: string[]
}

export interface MemoryCreateWeb {
  sourceType: 'WEB'
  url: string
}

export interface MemoryCreateNote {
  sourceType: 'NOTE'
  content: string
}

export type MemoryCreatePayload = MemoryCreateWeb | MemoryCreateNote

export interface RelatedMemory {
  id: string
  title: string
  summary: string
  type: string
  created_at: string
  similarity: number
}

export interface SearchResult {
  id: string
  title: string
  content: string
  summary: string | null
  source_type: SourceType
  similarity: number
  created_at?: string
  tags?: string[]
}
