export type SourceType = 'WEB' | 'PDF' | 'NOTE' | 'KAKAO' | 'CHAT_HISTORY' | 'JOURNAL'

export interface Scrap {
  id: string
  title: string
  summary: string | null
  source_type: SourceType
  created_at: string
  tags?: string[]
}

export interface ScrapCreateWeb {
  sourceType: 'WEB'
  url: string
}

export interface ScrapCreateNote {
  sourceType: 'NOTE'
  content: string
}

export type ScrapCreatePayload = ScrapCreateWeb | ScrapCreateNote

export interface ScrapDetail {
  id: string
  title: string
  content: string
  summary: string | null
  source_url: string | null
  source_type: SourceType
  tags: string[] | null
  created_at: string
  updated_at: string | null
}

export interface RelatedScrap {
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

export interface LinkedDiary {
  diary_id: string
  date: string
  preview: string
  mood: string | null
  link_type: string
}
