import { useEditor, EditorContent, type Editor } from '@tiptap/react'
import StarterKit from '@tiptap/starter-kit'
import Link from '@tiptap/extension-link'
import Placeholder from '@tiptap/extension-placeholder'
import Underline from '@tiptap/extension-underline'
import { useEffect, useCallback, useImperativeHandle, forwardRef } from 'react'
import { MemoryBlockNode } from './MemoryBlockNode'
import type { MemoryBlockAttrs } from './MemoryBlockNode'
import './TiptapEditor.css'

interface TiptapEditorProps {
  initialContent: string
  onUpdate: (html: string) => void
  onEditorReady?: (editor: Editor) => void
  editable?: boolean
}

export interface TiptapEditorHandle {
  getHTML: () => string
  setContent: (html: string) => void
  insertMemoryBlock: (attrs: MemoryBlockAttrs) => void
  getSelectedText: () => string
  replaceSelection: (text: string) => void
}

export const TiptapEditor = forwardRef<TiptapEditorHandle, TiptapEditorProps>(
  function TiptapEditor({ initialContent, onUpdate, onEditorReady, editable = true }, ref) {
    const editor = useEditor({
      extensions: [
        StarterKit.configure({
          heading: { levels: [1, 2, 3] },
        }),
        Link.configure({ openOnClick: false }),
        Placeholder.configure({ placeholder: '오늘 하루는 어떠셨나요? 자유롭게 기록해보세요...' }),
        Underline,
        MemoryBlockNode,
      ],
      content: initialContent,
      editable,
      onUpdate: ({ editor: e }) => {
        onUpdate(e.getHTML())
      },
    })

    useEffect(() => {
      if (editor) {
        editor.setEditable(editable)
      }
    }, [editor, editable])

    useEffect(() => {
      if (editor && onEditorReady) {
        onEditorReady(editor)
      }
    }, [editor, onEditorReady])

    const insertMemoryBlock = useCallback(
      (attrs: MemoryBlockAttrs) => {
        if (!editor) return
        editor
          .chain()
          .focus()
          .insertContent({
            type: 'memoryBlock',
            attrs,
          })
          .insertContent({ type: 'paragraph' })
          .run()
      },
      [editor],
    )

    useImperativeHandle(ref, () => ({
      getHTML: () => editor?.getHTML() ?? '',
      setContent: (html: string) => {
        editor?.commands.setContent(html)
      },
      insertMemoryBlock,
      getSelectedText: () => {
        if (!editor) return ''
        const { from, to } = editor.state.selection
        return editor.state.doc.textBetween(from, to, ' ')
      },
      replaceSelection: (text: string) => {
        if (!editor) return
        editor.chain().focus().insertContent(text).run()
      },
    }))

    if (!editor) return null

    return <EditorContent editor={editor} className="tiptap-editor" />
  },
)
