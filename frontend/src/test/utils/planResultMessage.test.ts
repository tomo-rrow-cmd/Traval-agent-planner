import { describe, expect, it } from 'vitest'
import { buildPlanResultMessage } from '@/utils/planResultMessage'

describe('buildPlanResultMessage', () => {
  it('生成最多三行的方案完成摘要', () => {
    const result = buildPlanResultMessage({
      destination: '北京',
      origin: '武汉',
      days: 3,
      trip_config: { travelers: 1 },
      budget: { actual_total: 1349, total_budget: 3000 },
      daily_itinerary: [{ day: 1, attractions: [{ name: '故宫' }] }],
      weather_forecast: [{ weather: '晴' }],
      traffic: { summary: '市内交通约20小时' },
    })

    expect(result).toBe([
      '✅ 北京3日方案已生成',
      '武汉 → 北京 · 3天 · 1人',
      '预计 ¥1349 / 预算 ¥3000',
    ].join('\n'))
    expect(result).not.toContain('故宫')
    expect(result).not.toContain('天气')
    expect(result).not.toContain('交通')
  })

  it('缺少参数时省略对应片段', () => {
    expect(buildPlanResultMessage({ destination: '上海' })).toBe(
      '✅ 上海旅行方案已生成\n上海',
    )
    expect(buildPlanResultMessage({})).toBe('✅ 旅行方案已生成')
  })

  it('兼容根级预算和人数数据', () => {
    expect(buildPlanResultMessage({
      destination: '杭州',
      days: '2',
      people_count: 2,
      estimated_cost: 1288.5,
      total_budget: 2500,
    })).toBe([
      '✅ 杭州2日方案已生成',
      '杭州 · 2天 · 2人',
      '预计 ¥1288.5 / 预算 ¥2500',
    ].join('\n'))
  })
})
