import { get, getBlob } from './client'

async function downloadFile(path: string, filename: string): Promise<void> {
  const blob = await getBlob(path)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

export async function exportMemories(): Promise<void> {
  await downloadFile('/export/memories', 'memoir_memories.json')
}

export async function exportJournals(): Promise<void> {
  await downloadFile('/export/journals', 'memoir_journals.zip')
}

export async function exportAll(): Promise<void> {
  await downloadFile('/export/all', 'memoir_backup.json')
}

export interface ExportCounts {
  memories: number
  journals: number
}

export async function fetchExportCounts(): Promise<ExportCounts> {
  return get<ExportCounts>('/export/counts')
}
