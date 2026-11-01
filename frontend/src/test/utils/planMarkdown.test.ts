import { describe, it, expect } from 'vitest'
import { generatePlanMarkdown } from '@/utils/planMarkdown'

describe('generatePlanMarkdown', () => {
  const fullSummary = {
    trip_name: '北京之旅',
    destination: '北京',
    origin: '上海',
    days: 2,
    daily_itinerary: [
      {
        day: 1,
        attractions: [
          { name: '故宫', reason: '必去景点', tags: '历史;文化' },
          { name: '天坛', reason: '世界遗产', tags: ['古建筑', '园林'] },
        ],
        meals: [
          { meal: '午餐', restaurant: '全聚德', avg_price: 150 },
        ],
        hotel: { name: '北京饭店' },
      },
    ],
    big_traffic: {
      trains: [
        { trainCode: 'G1', fromStationName: '上海虹桥', departureTime: '08:00',
          toStationName: '北京南', arrivalTime: '12:30', duration: '4h30m' },
      ],
    },
    budget: {
      total_budget: 5000,
      actual_total: 3200,
    },
  }

  it('generates markdown with all sections', () => {
    const result = generatePlanMarkdown(fullSummary)
    expect(result).toContain('# 🗺️ 北京之旅')
    expect(result).toContain('上海 → 北京')
    expect(result).toContain('## 📅 第1天')
    expect(result).toContain('### 故宫')
    expect(result).toContain('全聚德')
    expect(result).toContain('北京饭店')
    expect(result).toContain('## 🚄 推荐车次')
    expect(result).toContain('G1')
    expect(result).toContain('## 💰 预算')
    expect(result).toContain('¥5000')
  })

  it('handles missing origin gracefully', () => {
    const result = generatePlanMarkdown({ destination: '上海', days: 1 })
    expect(result).toContain('上海')
    expect(result).not.toContain('→')
  })

  it('handles empty summary without crashing', () => {
    const result = generatePlanMarkdown({})
    expect(result).toContain('0日之旅')
  })

  it('handles big_traffic as array', () => {
    const result = generatePlanMarkdown({
      destination: '北京',
      days: 1,
      big_traffic: [{ trainCode: 'K1', departureTime: '20:00', arrivalTime: '08:00', duration: '12h' }],
    })
    expect(result).toContain('K1')
  })

  it('handles missing budget gracefully', () => {
    const result = generatePlanMarkdown({ destination: '北京', days: 1 })
    expect(result).not.toContain('## 💰')
  })

  it('handles daily_plan fallback', () => {
    const result = generatePlanMarkdown({
      destination: '北京',
      days: 1,
      daily_plan: [{ day: 1, attractions: [{ name: '长城' }], meals: [] }],
    })
    expect(result).toContain('长城')
  })

  it('handles meal without price', () => {
    const result = generatePlanMarkdown({
      destination: '北京',
      days: 1,
      daily_itinerary: [{ day: 1, attractions: [], meals: [
        { meal: '早餐', restaurant: '小吃店' },
      ]}],
    })
    expect(result).toContain('小吃店')
    expect(result).not.toContain('¥')
  })
})
