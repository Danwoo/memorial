export interface OverviewStats {
  total_memories: number
  total_this_week: number
  total_this_month: number
  most_active_day: string | null
}

export interface ActivityData {
  date: string
  count: number
}

export interface SourceStats {
  source_type: string
  count: number
  percentage: number
}

export interface TagStats {
  tag: string
  count: number
}

export interface StatsData {
  overview: OverviewStats
  recent_activity: ActivityData[]
  sources: SourceStats[]
  top_tags: TagStats[]
}

export interface DigestMemory {
  id: string
  title: string
  type: string
  summary: string
  tags: string[]
}

export interface DigestJournal {
  id: string
  mood: string
  preview: string
  created_at: string
}

export interface StreakData {
  current_streak: number
  longest_streak: number
  total_active_days: number
  last_active_date: string | null
}

export interface ActivityResponse {
  days: number
  activity: ActivityData[]
}

export interface BriefingData {
  today_memories: {
    count: number
    topics: string[]
  }
  unreviewed_count: number
  streak: {
    current: number
    longest: number
  }
  suggested_question: string
  connection_hint: string | null
}

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
