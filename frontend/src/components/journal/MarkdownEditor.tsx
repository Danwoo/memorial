interface MarkdownEditorProps {
  content: string
  onChange: (content: string) => void
}

export function MarkdownEditor({ content, onChange }: MarkdownEditorProps) {
  return (
    <textarea
      className="markdown-raw-editor"
      value={content}
      onChange={(e) => onChange(e.target.value)}
      placeholder="마크다운으로 작성하세요..."
      spellCheck={false}
    />
  )
}
