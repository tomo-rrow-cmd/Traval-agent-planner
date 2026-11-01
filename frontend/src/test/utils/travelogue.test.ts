import { describe, expect, it } from 'vitest'
import { stripDuplicateTravelogueHeading } from '@/utils/travelogue'

describe('stripDuplicateTravelogueHeading', () => {
  it('移除与页面标题重复的旧版 Markdown 一级标题', () => {
    expect(stripDuplicateTravelogueHeading(
      '# 北京三日旅行手记\n\n## Day 1\n正文',
      '北京三日旅行手记',
    )).toBe('## Day 1\n正文')
  })

  it('保留不重复的正文标题', () => {
    const content = '# 行前说明\n\n## Day 1\n正文'
    expect(stripDuplicateTravelogueHeading(content, '北京三日旅行手记')).toBe(content)
  })
})
