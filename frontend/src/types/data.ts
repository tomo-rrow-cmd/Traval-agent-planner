// ============================================================
// 基础数据类型 — 对齐后端 app/schemas/data.py
// ============================================================

export interface City {
  id: string
  name: string
  province?: string
  country: string
  name_en?: string
  longitude?: number
  latitude?: number
  level?: string
  popular_rank?: number
  tags: string[]
  image_url?: string
  description?: string
}

export interface AttractionData {
  id: string
  name: string
  city: string
  address?: string
  longitude?: number
  latitude?: number
  level?: string
  rating?: number
  review_count: number
  ticket_price?: string
  open_time?: string
  suggest_duration?: number
  tags: string[]
  best_time?: string
  highlights?: string
  tips?: string
  image_url?: string
}

export interface RestaurantData {
  id: string
  name: string
  city: string
  address?: string
  longitude?: number
  latitude?: number
  cuisine?: string
  avg_price?: number
  rating?: number
  recommended_dishes: string[]
  open_time?: string
  need_booking: boolean
  tags: string[]
  tips?: string
}

export interface HotelData {
  id: string
  name: string
  city: string
  address?: string
  longitude?: number
  latitude?: number
  star_level?: number
  rating?: number
  price?: number
  room_types: string[]
  facilities: string[]
  tags: string[]
  distance_to_center_km?: number
}

export interface WeatherItem {
  date?: string
  weather: string
  temp_high?: number
  temp_low?: number
  wind?: string
  humidity?: number
  precipitation?: number
  aqi?: number
  advice?: string
}

export interface WeatherData {
  city: string
  forecasts: WeatherItem[]
}
