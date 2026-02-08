/** Payload for saving a journal entry */
export interface JournalSavePayload {
  content: string
}

/** Payload for fetching related memories based on journal content */
export interface RelatedMemoriesPayload {
  content: string
}
