import { describe, expect, it } from 'vitest'
import { mount, shallowMount } from '@vue/test-utils'
import { createTestingPinia } from '@pinia/testing'
import BlockRenderer from '@/components/plan/BlockRenderer.vue'
import DayCard from '@/components/plan/DayCard.vue'

const day = {
  day: 2,
  date: '2026-07-17',
  date_label: '7月17日',
  weather_summary: '多云 32℃ / 22℃',
  day_cost: 0,
  day_summary: '',
  activities: [
    { type: 'attraction', title: '圆明园遗址公园', cost: 0 },
    { type: 'attraction', title: '国家植物园', cost: 0 },
  ],
  meals: [],
}

describe('行程费用与车次展示', () => {
  it('当后端未提供日费用时，日卡片应包含当日交通费', () => {
    const wrapper = shallowMount(DayCard, {
      props: {
        day: day as any,
        expanded: true,
        traffic: [
          { from: '酒店', to: '圆明园', mode: 'transit', time_min: 211, cost: 22 },
          { from: '圆明园', to: '国家植物园', mode: 'transit', time_min: 90, cost: 9 },
          { from: '国家植物园', to: '酒店', mode: 'transit', time_min: 297, cost: 35 },
        ],
      },
      global: { plugins: [createTestingPinia()] },
    })

    expect(wrapper.find('.day-card__day-cost').text()).toBe('¥66')
  })

  it('应优先使用后端提供的日费用汇总', () => {
    const wrapper = shallowMount(DayCard, {
      props: {
        day: { ...day, day_cost: 128 } as any,
        traffic: [{ from: '酒店', to: '圆明园', mode: 'transit', time_min: 30, cost: 6 }],
      },
      global: { plugins: [createTestingPinia()] },
    })

    expect(wrapper.find('.day-card__day-cost').text()).toBe('¥128')
  })

  it('回退计算应累加活动、餐饮、住宿和交通', () => {
    const wrapper = shallowMount(DayCard, {
      props: {
        day: {
          ...day,
          activities: [{ type: 'attraction', title: '景点', cost: 20 }],
          meals: [{ meal: '午餐', restaurant: '餐厅', avg_price: 30 }],
          accommodation: { hotel_name: '酒店', price: 50 },
        } as any,
        traffic: [{ from: '酒店', to: '景点', mode: 'transit', time_min: 30, cost: 10 }],
      },
      global: { plugins: [createTestingPinia()] },
    })

    expect(wrapper.find('.day-card__day-cost').text()).toBe('¥110')
  })

  it('应清理历史方案中的酒店 Markdown 并允许逐段展开长地名', async () => {
    const dirtyHotel = String.raw`**喆·啡酒店\(北京天安门广场前门大街地铁站店\)**`
    const longDestination = '北京古代建筑博物馆先农坛园区东门游客服务中心'
    const wrapper = shallowMount(DayCard, {
      props: {
        day: {
          ...day,
          accommodation: { hotel_name: dirtyHotel, address: String.raw`前门大街\(地铁站旁\)`, price: 399 },
        } as any,
        expanded: true,
        traffic: [{
          from: dirtyHotel,
          to: longDestination,
          mode: 'transit',
          distance_km: 5,
          time_min: 35,
          cost: 4,
          plans: [
            {
              duration: 2100,
              cost: 4,
              walking_distance: 300,
              segments: [
                { type: 'walking', distance: 300, duration: 240 },
                { type: 'SUBWAY', line_name: '地铁7号线', departure_stop: '珠市口', arrival_stop: '广安门内', via_stops: 3, duration: 900 },
              ],
            },
            { duration: 2400, cost: 3, walking_distance: 500, segments: [{ type: 'BUS', line_name: '15路', departure_stop: '前门', arrival_stop: '南纬路', via_stops: 5 }] },
            { duration: 2700, cost: 5, walking_distance: 200, segments: [{ type: 'SUBWAY', line_name: '地铁8号线', departure_stop: '前门', arrival_stop: '天桥', via_stops: 2 }] },
            { duration: 3000, cost: 2, segments: [{ type: 'BUS', line_name: '备选4' }] },
          ],
        }],
      },
      global: { plugins: [createTestingPinia()] },
    })

    expect(wrapper.text()).toContain('喆·啡酒店(北京天安门广场前门大街地铁站店)')
    expect(wrapper.text()).not.toContain('**')
    expect(wrapper.text()).not.toContain(String.raw`\(`)

    const summary = wrapper.find('.traffic-row__summary')
    expect(summary.element.tagName).toBe('BUTTON')
    expect(summary.attributes('aria-expanded')).toBe('false')
    expect(wrapper.find('.traffic-row__place').attributes('title')).toBe('喆·啡酒店(北京天安门广场前门大街地铁站店)')

    await summary.trigger('click')

    expect(summary.attributes('aria-expanded')).toBe('true')
    expect(wrapper.text()).toContain(longDestination)
    expect(wrapper.text()).toContain('推荐方案')
    expect(wrapper.text()).toContain('备选方案 1')
    expect(wrapper.text()).toContain('备选方案 2')
    expect(wrapper.text()).not.toContain('备选方案 3')
    expect(wrapper.text()).toContain('地铁7号线')
    expect(wrapper.text()).toContain('珠市口 → 广安门内')
    expect(wrapper.text()).toContain('3站')
    expect(wrapper.text()).toContain('步行 300m')
  })

  it('估算交通段应保留费用并明确提示没有精确线路', async () => {
    const wrapper = shallowMount(DayCard, {
      props: {
        day: day as any,
        expanded: true,
        traffic: [{ from: '酒店', to: '故宫', mode: '地铁(est)', distance_km: 5, time_min: 12, cost: 15 }],
      },
      global: { plugins: [createTestingPinia()] },
    })

    expect(wrapper.text()).toContain('地铁（估算）')
    expect(wrapper.text()).toContain('¥15')

    await wrapper.find('.traffic-row__summary').trigger('click')

    expect(wrapper.text()).toContain('暂无精确线路数据')
    expect(wrapper.find('.traffic-row__estimate-note').exists()).toBe(true)
  })

  it('车次列表不应重复显示标题或固定的广州路线', () => {
    const wrapper = mount(BlockRenderer, {
      props: {
        blocks: [
          { type: 'section', data: { icon: 'train', title: '推荐车次', subtitle: '武汉 → 北京' } },
          {
            type: 'traffic_list',
            data: {
              trains: [
                {
                  trainCode: 'G66',
                  fromStationName: '武汉站',
                  toStationName: '北京西',
                  departureTime: '08:00',
                  arrivalTime: '12:00',
                  duration: '4h',
                  prices: { '商务座': 1600, '一等座': 830, '二等座': 520 },
                  firstClass: '无票',
                  secondClass: '12张',
                },
              ],
            },
          },
        ] as any,
      },
      global: {
        stubs: { DayCard: true, BudgetChart: true, MapContainer: true },
      },
    })

    expect(wrapper.text().match(/推荐车次/g)).toHaveLength(1)
    expect(wrapper.text()).toContain('武汉 → 北京')
    expect(wrapper.text()).not.toContain('广州 → 长沙')
    expect(wrapper.text()).toContain('12张')
    expect(wrapper.text()).toContain('无票')
    expect(wrapper.text()).toContain('余票未知')
    expect(wrapper.find('.block-traffic__availability--available').exists()).toBe(true)
    expect(wrapper.find('.block-traffic__availability--sold-out').exists()).toBe(true)
  })
})
