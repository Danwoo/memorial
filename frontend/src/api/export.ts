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

export async function exportScraps(): Promise<void> {
  if (isDemoMode()) return
  await downloadFile('/export/scraps', 'memoir_scraps.json')
}

export async function exportDiaries(): Promise<void> {
  if (isDemoMode()) return
  await downloadFile('/export/diaries', 'memoir_diaries.zip')
}

export async function exportAll(): Promise<void> {
  if (isDemoMode()) return
  await downloadFile('/export/all', 'memoir_backup.json')
}

export interface ExportCounts {
  scraps: number
  diaries: number
}

export async function fetchExportCounts(): Promise<ExportCounts> {
  if (isDemoMode()) return { scraps: 10, diaries: 7 }
  return get<ExportCounts>('/export/counts')
}
