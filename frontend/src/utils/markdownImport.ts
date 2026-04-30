const FRONTMATTER_RE = /^---\s*\n[\s\S]*?\n---\s*/

export function normalizeMarkdown(text: string) {
  return text
    .replace(/\r\n?/g, '\n')
    .replace(FRONTMATTER_RE, '')
    .trim()
}

export function markdownToPlain(text: string) {
  return normalizeMarkdown(text)
    .split('\n')
    .map((line) => cleanMarkdownLine(line))
    .filter(Boolean)
    .join('\n')
    .trim()
}

export function firstMarkdownHeading(text: string) {
  const match = normalizeMarkdown(text).match(/^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$/m)
  return match ? cleanMarkdownLine(match[1]) : ''
}

export function cleanFieldLabel(label: string) {
  return label
    .replace(/\s*\([^)]*\)\s*/g, '')
    .replace(/\s*（[^）]*）\s*/g, '')
    .replace(/[\/|]/g, ' ')
    .replace(/\s+/g, ' ')
    .trim()
}

export function extractMarkdownValue(text: string, labels: string[]) {
  const source = normalizeMarkdown(text)
  const normalizedLabels = labels.map(cleanFieldLabel).filter(Boolean)
  return (
    extractHeadingSection(source, normalizedLabels) ||
    extractLabeledBlock(source, normalizedLabels) ||
    ''
  ).trim()
}

export function extractMarkdownLines(text: string, labels: string[]) {
  return splitMarkdownLines(extractMarkdownValue(text, labels))
}

export function extractMarkdownNumber(text: string, labels: string[]) {
  const value = extractMarkdownValue(text, labels)
  const match = value.match(/(\d+(?:\.\d+)?)/)
  return match ? Number(match[1]) : null
}

function extractHeadingSection(source: string, labels: string[]) {
  const lines = source.split('\n')
  for (let i = 0; i < lines.length; i += 1) {
    const match = lines[i].match(/^\s{0,3}#{1,6}\s+(.+?)\s*#*\s*$/)
    if (!match) continue
    const title = cleanFieldLabel(cleanMarkdownLine(match[1]))
    if (!labels.some((label) => title === label || title.includes(label))) continue

    const section: string[] = []
    for (let j = i + 1; j < lines.length; j += 1) {
      if (/^\s{0,3}#{1,6}\s+/.test(lines[j])) break
      section.push(lines[j])
    }
    return cleanMarkdownBlock(section.join('\n'))
  }
  return ''
}

function extractLabeledBlock(source: string, labels: string[]) {
  const lines = source.split('\n')
  for (let i = 0; i < lines.length; i += 1) {
    const match = parseLabeledLine(lines[i], labels)
    if (!match) continue

    const block = match.value ? [match.value] : []
    for (let j = i + 1; j < lines.length; j += 1) {
      const line = lines[j]
      if (!line.trim()) {
        if (block.length > 0) break
        continue
      }
      if (/^\s{0,3}#{1,6}\s+/.test(line)) break
      if (isLikelyLabeledLine(line) && block.length > 0) break
      block.push(line)
    }
    return cleanMarkdownBlock(block.join('\n'))
  }
  return ''
}

function parseLabeledLine(line: string, labels: string[]) {
  const normalizedLine = line
    .replace(/^\s*(?:[-*+]|\d+\.)\s+/, '')
    .replace(/^\s*>+\s*/, '')
  const match = normalizedLine.match(/^\s*(?:\*\*)?(.{1,24}?)(?:\*\*)?\s*[:：]\s*(.*)$/)
  if (!match) return null

  const label = cleanFieldLabel(match[1])
  if (!labels.some((item) => label === item || label.includes(item))) return null
  return { value: match[2] || '' }
}

function isLikelyLabeledLine(line: string) {
  const normalizedLine = line
    .replace(/^\s*(?:[-*+]|\d+\.)\s+/, '')
    .replace(/^\s*>+\s*/, '')
  return /^\s*(?:\*\*)?.{1,24}?(?:\*\*)?\s*[:：]/.test(normalizedLine)
}

function splitMarkdownLines(value: string) {
  return value
    .split(/\n|[;；]/)
    .map((line) => cleanMarkdownLine(line))
    .filter(Boolean)
}

function cleanMarkdownBlock(value: string) {
  return value
    .split('\n')
    .map((line) => cleanMarkdownLine(line))
    .filter(Boolean)
    .join('\n')
    .trim()
}

function cleanMarkdownLine(line: string) {
  return line
    .replace(/^\s{0,3}#{1,6}\s+/, '')
    .replace(/^\s*(?:[-*+]|\d+\.)\s+/, '')
    .replace(/^\s*>+\s*/, '')
    .replace(/\*\*/g, '')
    .replace(/`/g, '')
    .trim()
}
