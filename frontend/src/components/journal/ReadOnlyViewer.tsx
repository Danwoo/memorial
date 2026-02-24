import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { rehypeSanitize, sanitizeSchema } from '../../utils/markdownSanitize'

interface ReadOnlyViewerProps {
  content: string
}

export function ReadOnlyViewer({ content }: ReadOnlyViewerProps) {
  return (
    <div className="readonly-viewer">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[[rehypeSanitize, sanitizeSchema]]}
      >
        {content}
      </ReactMarkdown>
    </div>
  )
}
