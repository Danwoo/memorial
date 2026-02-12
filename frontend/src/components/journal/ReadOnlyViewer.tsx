import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

interface ReadOnlyViewerProps {
  content: string
}

export function ReadOnlyViewer({ content }: ReadOnlyViewerProps) {
  return (
    <div className="readonly-viewer">
      <ReactMarkdown remarkPlugins={[remarkGfm]}>{content}</ReactMarkdown>
    </div>
  )
}
