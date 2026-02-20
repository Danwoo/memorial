import { Globe, FileText, StickyNote, File } from 'lucide-react'

interface SourceIconProps {
  type: string
  size?: number
}

export default function SourceIcon({ type, size = 16 }: SourceIconProps) {
  switch (type) {
    case 'WEB': return <Globe size={size} />
    case 'PDF': return <FileText size={size} />
    case 'NOTE': return <StickyNote size={size} />
    default: return <File size={size} />
  }
}
