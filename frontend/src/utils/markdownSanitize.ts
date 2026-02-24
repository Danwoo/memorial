import rehypeSanitize, { defaultSchema } from 'rehype-sanitize'
import type { Options } from 'rehype-sanitize'

const blockedTags = ['script', 'iframe', 'object', 'embed', 'form', 'input', 'img']

export const sanitizeSchema: Options = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    a: [
      ...(defaultSchema.attributes?.a || []),
      ['target', '_blank'],
      ['rel', 'noopener', 'noreferrer'],
    ],
    img: [],
    code: [
      ...(defaultSchema.attributes?.code || []),
    ],
  },
  tagNames: [
    ...(defaultSchema.tagNames || []).filter(
      (tag) => !blockedTags.includes(tag)
    ),
  ],
  protocols: {
    href: ['http', 'https', 'mailto'],
  },
  strip: ['script', 'iframe', 'object', 'embed', 'form'],
}

export { rehypeSanitize }
