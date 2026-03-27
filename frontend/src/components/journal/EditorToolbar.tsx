import type { Editor } from '@tiptap/react'
import type { EditorMode } from '../../types'
import {
  Bold, Italic, Underline, Strikethrough,
  Heading1, Heading2, Heading3,
  List, ListOrdered, Quote, Minus,
  Link2, ImageIcon, CheckSquare,
  Undo2, Redo2,
  type LucideIcon,
} from 'lucide-react'
import './EditorToolbar.css'

interface EditorToolbarProps {
  editor: Editor | null
  mode: EditorMode
  onModeChange: (mode: EditorMode) => void
}

type ToolbarItem =
  | { kind: 'divider' }
  | { kind: 'button'; icon: LucideIcon; action: () => void; active?: string; activeAttrs?: Record<string, unknown>; label: string }

export function EditorToolbar({ editor, mode, onModeChange }: EditorToolbarProps) {
  const isWysiwyg = mode === 'wysiwyg'

  const handleLink = () => {
    if (!editor) return
    const url = window.prompt('URL을 입력하세요:')
    if (url) {
      editor.chain().focus().setLink({ href: url }).run()
    }
  }

  const handleImage = () => {
    if (!editor) return
    const url = window.prompt('이미지 URL을 입력하세요:')
    if (url) {
      editor.chain().focus().setImage({ src: url }).run()
    }
  }

  const items: ToolbarItem[] = [
    { kind: 'button', icon: Bold, action: () => { editor?.chain().focus().toggleBold().run() }, active: 'bold', label: 'Bold' },
    { kind: 'button', icon: Italic, action: () => { editor?.chain().focus().toggleItalic().run() }, active: 'italic', label: 'Italic' },
    { kind: 'button', icon: Underline, action: () => { editor?.chain().focus().toggleUnderline().run() }, active: 'underline', label: 'Underline' },
    { kind: 'button', icon: Strikethrough, action: () => { editor?.chain().focus().toggleStrike().run() }, active: 'strike', label: 'Strikethrough' },
    { kind: 'divider' },
    { kind: 'button', icon: Heading1, action: () => { editor?.chain().focus().toggleHeading({ level: 1 }).run() }, active: 'heading', activeAttrs: { level: 1 }, label: 'H1' },
    { kind: 'button', icon: Heading2, action: () => { editor?.chain().focus().toggleHeading({ level: 2 }).run() }, active: 'heading', activeAttrs: { level: 2 }, label: 'H2' },
    { kind: 'button', icon: Heading3, action: () => { editor?.chain().focus().toggleHeading({ level: 3 }).run() }, active: 'heading', activeAttrs: { level: 3 }, label: 'H3' },
    { kind: 'divider' },
    { kind: 'button', icon: List, action: () => { editor?.chain().focus().toggleBulletList().run() }, active: 'bulletList', label: 'Bullet list' },
    { kind: 'button', icon: ListOrdered, action: () => { editor?.chain().focus().toggleOrderedList().run() }, active: 'orderedList', label: 'Ordered list' },
    { kind: 'button', icon: Quote, action: () => { editor?.chain().focus().toggleBlockquote().run() }, active: 'blockquote', label: 'Blockquote' },
    { kind: 'button', icon: Minus, action: () => { editor?.chain().focus().setHorizontalRule().run() }, label: 'Divider' },
    { kind: 'button', icon: Link2, action: handleLink, active: 'link', label: 'Link' },
    { kind: 'button', icon: ImageIcon, action: handleImage, label: 'Image' },
    { kind: 'button', icon: CheckSquare, action: () => { editor?.chain().focus().toggleTaskList().run() }, active: 'taskList', label: 'Checklist' },
    { kind: 'divider' },
    { kind: 'button', icon: Undo2, action: () => { editor?.chain().focus().undo().run() }, label: 'Undo' },
    { kind: 'button', icon: Redo2, action: () => { editor?.chain().focus().redo().run() }, label: 'Redo' },
  ]

  return (
    <div className="editor-toolbar">
      <div className="toolbar-formats">
        {items.map((item, i) => {
          if (item.kind === 'divider') {
            return <span key={i} className="toolbar-divider" />
          }
          const { icon: Icon, action, active, activeAttrs, label } = item
          const isActive = active
            ? activeAttrs
              ? editor?.isActive(active, activeAttrs)
              : editor?.isActive(active)
            : false
          return (
            <button
              key={i}
              className={`toolbar-btn ${isActive ? 'toolbar-btn--active' : ''}`}
              onClick={action}
              disabled={!isWysiwyg}
              title={label}
              type="button"
            >
              <Icon size={16} />
            </button>
          )
        })}
      </div>
      <div className="toolbar-modes">
        {(['wysiwyg', 'markdown', 'viewer'] as EditorMode[]).map((m) => (
          <button
            key={m}
            className={`mode-btn ${mode === m ? 'mode-btn--active' : ''}`}
            onClick={() => onModeChange(m)}
            type="button"
          >
            {m === 'wysiwyg' ? '편집기' : m === 'markdown' ? '마크다운' : '뷰어'}
          </button>
        ))}
      </div>
    </div>
  )
}
