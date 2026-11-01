import { describe, it, expect } from 'vitest'
import { mount } from '@vue/test-utils'
import ActivityItem from '@/components/plan/ActivityItem.vue'
import type { Activity } from '@/types/plan'

const mockActivity: Activity = {
  type: 'attraction',
  title: '大理古城',
  time_slot: '09:00-11:00',
  description: '漫步古城，感受白族文化',
  location: { lat: 25.68, lng: 100.16 },
  duration_minutes: 120,
  tips: '建议早起避开人流',
  cost: 0,
  tags: [],
}

const mockFoodActivity: Activity = {
  type: 'food',
  title: '白族风味午餐',
  time_slot: '12:00-13:00',
  description: '品尝地道白族美食',
  location: { lat: 25.68, lng: 100.16 },
  duration_minutes: 60,
  cost: 80,
  tags: [],
}

const globalStubs = {
  IconTravel: true,
  aButton: { template: '<button><slot /></button>' },
}

describe('ActivityItem 组件渲染', () => {
  it('应正确渲染活动标题', () => {
    const wrapper = mount(ActivityItem, {
      props: { activity: mockActivity },
      global: { stubs: globalStubs },
    })

    expect(wrapper.text()).toContain('大理古城')
  })

  it('应正确渲染时间段', () => {
    const wrapper = mount(ActivityItem, {
      props: { activity: mockActivity },
      global: { stubs: globalStubs },
    })

    expect(wrapper.text()).toContain('09:00-11:00')
  })

  it('应正确渲染活动类型标签', () => {
    const wrapper = mount(ActivityItem, {
      props: { activity: mockActivity },
      global: { stubs: globalStubs },
    })

    expect(wrapper.text()).toContain('景点')
  })

  it('美食活动应显示 food 类型标签', () => {
    const wrapper = mount(ActivityItem, {
      props: { activity: mockFoodActivity },
      global: { stubs: globalStubs },
    })

    expect(wrapper.text()).toContain('美食')
    expect(wrapper.text()).toContain('白族风味午餐')
  })

  it('点击展开应显示描述和提示', async () => {
    const wrapper = mount(ActivityItem, {
      props: { activity: mockActivity },
      global: { stubs: globalStubs },
    })

    await wrapper.trigger('click')

    expect(wrapper.text()).toContain('漫步古城')
    expect(wrapper.text()).toContain('建议早起避开人流')
  })
})
