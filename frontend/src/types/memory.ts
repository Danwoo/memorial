/** Source types for memory entries */
export type SourceType = 'WEB' | 'PDF' | 'NOTE'

/** A stored memory item */
export interface Memory {
  id: string
  title: string
  summary: string | null
  source_type: SourceType
  created_at: string
  tags?: string[]
}

/** Payload for creating a web-based memory */
export interface MemoryCreateWeb {
  sourceType: 'WEB'
  url: string
}

/** Payload for creating a note-based memory */
export interface MemoryCreateNote {
  sourceType: 'NOTE'
  content: string
}

export type MemoryCreatePayload = MemoryCreateWeb | MemoryCreateNote

/** Related memory shown in journal context sidebar */
export interface RelatedMemory {
  id: string
  title: string
  summary: string
  type: string
  created_at: string
  similarity: number
}

/** Search result returned from semantic search */
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
