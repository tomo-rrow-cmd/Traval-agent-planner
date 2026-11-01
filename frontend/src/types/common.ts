/* ============================================================
   通用类型与枚举
   ============================================================ */

/** 基础数据 - 城市 */
export interface City {
  id: string
  name: string
  province: string
  country: string
  name_en: string
  longitude: number
  latitude: number
  level: string
  popular_rank: number
  tags: string[]
  image_url: string
  description: string
}

/** 基础数据 - 景点 */
export interface Attraction {
  id: string
  name: string
  city: string
  address: string
  longitude: number
  latitude: number
  level: string
  rating: number
  review_count: number
  ticket_price: string
  open_time: string
  suggest_duration: number
  tags: string[]
  best_time: string
  highlights: string
  tips: string
  image_url: string
}

/** 基础数据 - 餐厅 */
export interface Restaurant {
  id: string
  name: string
  city: string
  address: string
  longitude: number
  latitude: number
  cuisine: string
  avg_price: number
  rating: number
  recommended_dishes: string[]
  open_time: string
  need_booking: boolean
  tags: string[]
  tips: string
}

/** 基础数据 - 酒店 */
export interface Hotel {
  id: string
  name: string
  city: string
  address: string
  longitude: number
  latitude: number
  star_level: number
  rating: number
  price: number
  room_types: string[]
  facilities: string[]
  tags: string[]
  distance_to_center_km: number
}

/** 天气查询响应 */
export interface WeatherResponse {
  city: string
  forecasts: Array<{
    date: string
    weather: string
    temp_high: number
    temp_low: number
    wind: string
    humidity: number
    precipitation: number
    aqi: number
    advice: string
  }>
}

/** 健康检查响应 */
export interface HealthCheckResponse {
  status: string
  version: string
  uptime_seconds: number
  dependencies: Record<string, string>
}

/** 健康数据（用于 API ops） */
export type HealthData = HealthCheckResponse

/** 异步任务状态 */
export interface TaskStatus {
  task_id: string
  type?: string
  status: 'processing' | 'completed' | 'failed'
  progress?: number
  message?: string
  download_url?: string
  expires_at?: string
  error?: {
    code: number
    message: string
  }
}

/** 分享方案 */
export interface ShareRequestParams {
  expire_in?: number
  password?: string
}
