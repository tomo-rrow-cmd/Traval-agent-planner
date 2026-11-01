import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import BudgetOverviewCard from '@/components/plan/BudgetOverviewCard.vue'

describe('预算概览卡片', () => {
  it('应在一张卡片中合并预算分布和执行分析', () => {
    const wrapper = mount(BudgetOverviewCard, {
      props: {
        total: 5000,
        estimated: 4650,
        breakdown: {
          accommodation: { amount: 1500, percent: 30, items: [] },
          transport: { amount: 700, percent: 14, items: [] },
          food: { amount: 900, percent: 18, items: [] },
        },
        details: [
          { category: '住宿', budget: 1400, spent: 1500, status: 'over' },
          { category: '交通', budget: 800, spent: 700, status: 'ok' },
        ],
        warnings: ['住宿超预算 ¥100'],
        suggestions: ['选择地铁附近酒店'],
      },
    })

    expect(wrapper.text()).toContain('预算概览')
    expect(wrapper.text()).toContain('分类明细')
    expect(wrapper.text()).toContain('住宿超预算 ¥100')
    expect(wrapper.text()).toContain('选择地铁附近酒店')
    expect(wrapper.text()).not.toContain('预算分布')
    expect(wrapper.find('.budget-overview-card__detail-status--over').exists()).toBe(true)
  })
})
