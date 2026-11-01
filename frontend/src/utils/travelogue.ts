export function stripDuplicateTravelogueHeading(content: string, title: string): string {
  const firstHeading = content.match(/^#\s+(.+)\r?\n+/)
  return firstHeading?.[1]?.trim() === title.trim()
    ? content.slice(firstHeading[0].length)
    : content
}
