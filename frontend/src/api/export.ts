import { get, getBlob } from './client'
import { isDemoMode } from '../contexts/DemoContext'

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
  if (isDemoMode()) return
  await downloadFile('/export/memories', 'memoir_memories.json')
}

export async function exportJournals(): Promise<void> {
  if (isDemoMode()) return
  await downloadFile('/export/journals', 'memoir_journals.zip')
}

export async function exportAll(): Promise<void> {
  if (isDemoMode()) return
  await downloadFile('/export/all', 'memoir_backup.json')
}

export interface ExportCounts {
  memories: number
  journals: number
}

export async function fetchExportCounts(): Promise<ExportCounts> {
  if (isDemoMode()) return { memories: 10, journals: 7 }
  return get<ExportCounts>('/export/counts')
}
