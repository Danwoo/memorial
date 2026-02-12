import { Node, mergeAttributes } from '@tiptap/core'

export interface MemoryBlockAttrs {
  memoryId: string
  title: string
  summary: string
  type: string
}

export const MemoryBlockNode = Node.create({
  name: 'memoryBlock',
  group: 'block',
  atom: true,

  addAttributes() {
    return {
      memoryId: { default: '' },
      title: { default: '' },
      summary: { default: '' },
      type: { default: '' },
    }
  },

  parseHTML() {
    return [{ tag: 'div[data-memory-block]' }]
  },

  renderHTML({ HTMLAttributes }) {
    return [
      'div',
      mergeAttributes(HTMLAttributes, {
        'data-memory-block': '',
        class: 'memory-block-embed',
      }),
      [
        'div',
        { class: 'memory-block-type' },
        HTMLAttributes.type || '',
      ],
      [
        'div',
        { class: 'memory-block-title' },
        HTMLAttributes.title || '',
      ],
      [
        'div',
        { class: 'memory-block-summary' },
        HTMLAttributes.summary || '',
      ],
    ]
  },
})
