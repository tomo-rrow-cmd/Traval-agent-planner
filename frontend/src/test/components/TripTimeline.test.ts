import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import TripTimeline from '@/components/trip/TripTimeline.vue'

const checkInButtonStub = {
  props: ['poiType', 'poiName'],
  template: '<button>{{ poiName }}</button>',
}

describe('TripTimeline 日期切换', () => {
  it('切换日期后应立即渲染新一天的行程', async () => {
    const wrapper = mount(TripTimeline, {
      props: {
        checkins: [],
        currentDay: 1,
        planSlots: [
          { time: '09:00', type: 'attraction', name: '玉渊潭公园' },
          { time: '12:00', type: 'restaurant', name: '北京烤鸭' },
        ],
      },
      global: { stubs: { CheckInButton: checkInButtonStub } },
    })

    expect(wrapper.text()).toContain('玉渊潭公园')
    expect(wrapper.text()).not.toContain('故宫博物院')

    await wrapper.setProps({
      currentDay: 2,
      planSlots: [
        { time: '08:30', type: 'attraction', name: '故宫博物院' },
        { time: '14:00', type: 'attraction', name: '景山公园' },
      ],
    })

    expect(wrapper.text()).toContain('故宫博物院')
    expect(wrapper.text()).toContain('景山公园')
    expect(wrapper.text()).not.toContain('玉渊潭公园')
    expect(wrapper.text()).not.toContain('北京烤鸭')
  })
})
