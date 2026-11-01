/* ============================================================
   基础数据 API
   对应文档：API接口规范文档.md · §6 基础数据接口
   ============================================================ */

import http from './http'
import type { ApiResponse, PaginatedData } from '@/types/api'
import type { City, Attraction, Restaurant, Hotel, WeatherResponse } from '@/types/common'

/** 获取热门城市列表 */
export function getPopularCities() {
  return http.get<ApiResponse<City[]>>('/data/cities', { params: { popular: true } })
}

/** 搜索城市 */
export function searchCities(keyword: string) {
  return http.get<ApiResponse<City[]>>('/data/cities', { params: { keyword } })
}

/** 获取景点列表 */
export function getAttractions(params: {
  city: string
  tags?: string
  page?: number
  page_size?: number
}) {
  return http.get<ApiResponse<PaginatedData<Attraction>>>('/data/attractions', { params })
}

/** 获取景点详情 */
export function getAttractionDetail(id: string) {
  return http.get<ApiResponse<Attraction>>(`/data/attractions/${id}`)
}

/** 获取餐厅列表 */
export function getRestaurants(params: {
  city: string
  cuisine?: string
  page?: number
  page_size?: number
}) {
  return http.get<ApiResponse<PaginatedData<Restaurant>>>('/data/restaurants', { params })
}

/** 获取酒店列表 */
export function getHotels(params: {
  city: string
  price_range?: string
  page?: number
  page_size?: number
}) {
  return http.get<ApiResponse<PaginatedData<Hotel>>>('/data/hotels', { params })
}

/** 查询天气 */
export function getWeather(params: { city: string; date?: string }) {
  return http.get<ApiResponse<WeatherResponse>>('/data/weather', { params })
}
