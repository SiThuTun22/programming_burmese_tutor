import type { Components } from 'react-markdown'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { normalizeMarkdownTables } from '../lib/normalizeMarkdownTables'

const components: Components = {
  table: ({ children, ...props }) => (
    <div className="my-3 w-full overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-600">
      <table
        className="w-full min-w-[16rem] border-collapse text-left text-sm"
        {...props}
      >
        {children}
      </table>
    </div>
  ),
  thead: ({ children, ...props }) => (
    <thead className="bg-slate-100 dark:bg-slate-800" {...props}>
      {children}
    </thead>
  ),
  th: ({ children, ...props }) => (
    <th
      className="border-b border-slate-200 px-3 py-2 font-semibold dark:border-slate-600"
      {...props}
    >
      {children}
    </th>
  ),
  td: ({ children, ...props }) => (
    <td
      className="border-b border-slate-100 px-3 py-2 align-top dark:border-slate-700"
      {...props}
    >
      {children}
    </td>
  ),
  tr: ({ children, ...props }) => (
    <tr className="even:bg-slate-50/80 dark:even:bg-slate-800/40" {...props}>
      {children}
    </tr>
  ),
}

type Props = {
  content: string
}

export function MarkdownMessage({ content }: Props) {
  const normalized = normalizeMarkdownTables(content)
  return (
    <div className="message-markdown text-sm leading-relaxed [&_p]:my-1.5 [&_ul]:my-2 [&_ol]:my-2 [&_li]:my-0.5">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {normalized}
      </ReactMarkdown>
    </div>
  )
}
