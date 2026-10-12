/**
 * GFM tables need one row per line. Models often collapse rows onto one line.
 */
export function normalizeMarkdownTables(content: string): string {
  if (!content.includes('|')) {
    return content
  }

  let text = content

  // Header row then separator on same line: "| A | B | |---|---|"
  text = text.replace(
    /(\|[^|\n]+(?:\|[^|\n]+)+\|)\s+(\|[-:\s|]+\|)/g,
    '$1\n$2',
  )

  // Separator then body row: "|---|---| | C | D |"
  text = text.replace(
    /(\|[-:\s|]+\|)\s+(\|[^|\n]+(?:\|[^|\n]+)+\|)/g,
    '$1\n$2',
  )

  // Body rows glued together: "| C | D | | E | F |"
  text = text.replace(
    /(\|[^|\n]+(?:\|[^|\n]+)+\|)\s+(?=\|[^|\n-])/g,
    '$1\n',
  )

  return text
}
