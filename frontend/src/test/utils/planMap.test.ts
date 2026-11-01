import { describe, expect, it } from 'vitest'
import { buildDailyMapData, getMapPosition, normalizeMapMarkerType } from '@/utils/planMap'

describe('每日地图路线组装', () => {
  it('应按酒店、活动、午餐、活动、晚餐、酒店生成闭环路线', () => {
    const result = buildDailyMapData({
      activities: [
        { title: '博物馆', type: 'attraction', location: { lng: 116.40, lat: 39.90 } },
        { title: '商场', type: 'shopping', longitude: 116.44, latitude: 39.94 },
      ],
      meals: [
        { meal: '午餐', restaurant: '午餐厅', longitude: 116.42, latitude: 39.92 },
        { meal: '晚餐', restaurant: '晚餐厅', coordinates: { lng: 116.46, lat: 39.96 } },
      ],
    }, {
      name: '测试酒店',
      longitude: 116.38,
      latitude: 39.88,
    })

    expect(result.markers.map(marker => marker.title)).toEqual([
      '测试酒店',
      '博物馆',
      '午餐厅',
      '商场',
      '晚餐厅',
    ])
    expect(result.markers.map(marker => marker.type)).toEqual([
      'accommodation',
      'attraction',
      'food',
      'shopping',
      'food',
    ])
    expect(result.routePath).toEqual([
      [116.38, 39.88],
      [116.40, 39.90],
      [116.42, 39.92],
      [116.44, 39.94],
      [116.46, 39.96],
      [116.38, 39.88],
    ])
  })

  it('应兼容坐标字段别名并忽略无效坐标', () => {
    expect(getMapPosition({ longitude: '120.1', latitude: '30.2' })).toEqual([120.1, 30.2])
    expect(getMapPosition({ location: { lng: 181, lat: 30 } })).toBeNull()
    expect(getMapPosition({ latitude: 30 })).toBeNull()
    expect(normalizeMapMarkerType('restaurant')).toBe('food')
    expect(normalizeMapMarkerType('hotel')).toBe('accommodation')
    expect(normalizeMapMarkerType('unknown')).toBe('attraction')
  })

  it('没有酒店时也应保留餐饮和活动点位且不强制闭环', () => {
    const result = buildDailyMapData({
      activities: [{ name: '景点', latitude: 25.1, longitude: 110.1 }],
      meals: [{ meal: '午餐', restaurant: '餐厅', latitude: 25.2, longitude: 110.2 }],
    })

    expect(result.markers).toHaveLength(2)
    expect(result.routePath).toEqual([[110.1, 25.1], [110.2, 25.2]])
  })
})
