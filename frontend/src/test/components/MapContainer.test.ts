import { flushPromises, mount } from '@vue/test-utils'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import MapContainer from '@/components/map/MapContainer.vue'

const amapState = vi.hoisted(() => ({
  markerOptions: [] as any[],
}))

vi.mock('@amap/amap-jsapi-loader', () => ({
  default: {
    load: vi.fn(async () => {
      class FakeMap {
        add() {}
        remove() {}
        setFitView() {}
        setCenter() {}
        resize() {}
        destroy() {}
      }
      class FakeMarker {
        options: any
        constructor(options: any) {
          this.options = options
          amapState.markerOptions.push(options)
        }
        on() {}
      }
      return {
        Map: FakeMap,
        Marker: FakeMarker,
        TileLayer: class {},
        Pixel: class {
          constructor(public x: number, public y: number) {}
        },
      }
    }),
  },
}))

describe('MapContainer 地图标志', () => {
  beforeEach(() => {
    amapState.markerOptions = []
  })

  it('酒店、餐饮和景点应显示不同图标、颜色及图例', async () => {
    const wrapper = mount(MapContainer, {
      props: {
        markers: [
          { position: [116.38, 39.88], title: '测试酒店', type: 'accommodation' },
          { position: [116.40, 39.90], title: '测试餐厅', type: 'food' },
          { position: [116.42, 39.92], title: '测试景点', type: 'attraction' },
        ],
      },
    })
    await flushPromises()

    expect(wrapper.findAll('.map-container__legend-item').map(item => item.text())).toEqual([
      '酒店',
      '餐饮',
      '景点',
    ])
    expect(amapState.markerOptions).toHaveLength(3)

    const markerContents = amapState.markerOptions.map(options => options.content as HTMLElement)
    expect(markerContents.map(element => element.getAttribute('aria-label'))).toEqual([
      '酒店: 测试酒店',
      '餐饮: 测试餐厅',
      '景点: 测试景点',
    ])
    expect(new Set(markerContents.map(element => element.style.background))).toHaveLength(3)
    expect(new Set(markerContents.map(element => element.innerHTML))).toHaveLength(3)

    wrapper.unmount()
  })
})
