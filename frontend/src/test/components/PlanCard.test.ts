import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import PlanCard from '@/components/plan/PlanCard.vue'
import type { PlanSummary } from '@/types/plan'

const mockPlan: PlanSummary = {
  id: 'plan_001',
  title: '云南大理5日游',
  destination: '云南大理',
  start_date: '2026-07-01',
  end_date: '2026-07-05',
  days: 5,
  estimated_cost: 4500,
  travel_style: '深度游',
  status: 'completed',
  is_favorite: false,
  created_at: '2026-07-01T10:00:00Z',
}

describe('PlanCard 组件渲染', () => {
  it('应正确渲染目的地名称', () => {
    const wrapper = mount(PlanCard, {
      props: { plan: mockPlan },
      global: { stubs: { IconTravel: true, aButton: true } },
    })

    expect(wrapper.text()).toContain('云南大理')
  })

  it('应正确渲染天数', () => {
    const wrapper = mount(PlanCard, {
      props: { plan: mockPlan },
      global: { stubs: { IconTravel: true, aButton: true } },
    })

    expect(wrapper.text()).toContain('5')
  })

  it('应正确渲染预算', () => {
    const wrapper = mount(PlanCard, {
      props: { plan: mockPlan },
      global: { stubs: { IconTravel: true, aButton: true } },
    })

    expect(wrapper.text()).toContain('¥')
  })

  it('点击时应触发 click 事件', async () => {
    const wrapper = mount(PlanCard, {
      props: { plan: mockPlan },
      global: { stubs: { IconTravel: true, aButton: true } },
    })

    await wrapper.trigger('click')
    expect(wrapper.emitted('click')).toBeTruthy()
  })
})
