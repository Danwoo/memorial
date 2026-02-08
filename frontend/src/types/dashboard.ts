/** Overview statistics for the dashboard */
export interface OverviewStats {
  total_memories: number
  total_this_week: number
  total_this_month: number
  most_active_day: string | null
}

/** Single day activity data point */
export interface ActivityData {
  date: string
  count: number
}

/** Source type distribution stat */
export interface SourceStats {
  source_type: string
  count: number
  percentage: number
}

/** Tag frequency stat */
export interface TagStats {
  tag: string
  count: number
}

/** Aggregated stats data for the dashboard */
export interface StatsData {
  overview: OverviewStats
  recent_activity: ActivityData[]
  sources: SourceStats[]
  top_tags: TagStats[]
}

/** A memory entry within today's digest */
export interface DigestMemory {
  id: string
  title: string
  type: string
  summary: string
  tags: string[]
}

/** Single journal entry within today's digest */
export interface DigestJournal {
  id: string
  mood: string
  preview: string
  created_at: string
}

/** Today's digest data */
export interface DigestData {
  date: string
  summary: {
    memory_count: number
    journal_count: number
    chat_count: number
  }
  memories: DigestMemory[]
  journals: DigestJournal[]
  chats: Record<string, unknown>[]
  insights: {
    main_topics: string[]
    suggested_questions: string[]
  }
}
