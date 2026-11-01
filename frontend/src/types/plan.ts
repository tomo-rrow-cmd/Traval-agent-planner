/* ============================================================
   方案相关类型定义
   对应文档：API接口规范文档.md · §5
   ============================================================ */

import type { PaginationParams } from './api'

/* ========== 活动类型 ========== */

export type ActivityType =
  | 'transport'
  | 'attraction'
  | 'food'
  | 'shopping'
  | 'rest'
  | 'entertainment'
  | 'accommodation'

export const ACTIVITY_TYPES: ActivityType[] = [
  'transport',
  'attraction',
  'food',
  'shopping',
  'rest',
  'entertainment',
  'accommodation',
]

export const ACTIVITY_TYPE_LABELS: Record<ActivityType, string> = {
  transport: '交通',
  attraction: '景点',
  food: '美食',
  shopping: '购物',
  rest: '休息',
  entertainment: '娱乐',
  accommodation: '住宿',
}

export const ACTIVITY_TYPE_ICONS: Record<ActivityType, string> = {
  transport: 'plane',
  attraction: 'landmark',
  food: 'utensils-crossed',
  shopping: 'shopping-bag',
  rest: 'coffee',
  entertainment: 'ticket',
  accommodation: 'bed-double',
}

/* ========== 方案列表 ========== */

export type PlanStatus = 'draft' | 'completed' | 'failed'

/** 方案列表请求参数 */
export interface PlanListParams extends PaginationParams {
  status?: PlanStatus
}

/** 方案摘要 */
export interface PlanSummary {
  id: string
  title: string
  destination: string
  start_date: string
  end_date: string
  days: number
  estimated_cost: number
  travel_style: string
  status: PlanStatus
  is_favorite: boolean
  created_at: string
}

/* ========== 方案详情 ========== */

/** 位置坐标 */
export interface GeoLocation {
  lat: number
  lng: number
}

/** 方案概览 */
export interface PlanOverview {
  highlights: string[]
  total_distance_km: number
  transport_modes: string[]
}

/** 单日活动 */
export interface DayActivity {
  time_slot: string
  type: ActivityType
  title: string
  subtitle?: string
  description: string
  location: GeoLocation
  cost: number
  tips?: string
  duration_minutes?: number
  rating?: number
  tags?: string[]
  // --- compat fields from SSE data ---
  name?: string
  duration_hours?: number
  price?: number
  reason?: string
  coordinates?: { lat: number; lng: number }
  longitude?: number
  latitude?: number
}

/** 住宿信息 */
export interface Accommodation {
  hotel_name: string
  address: string
  room_type: string
  price: number
  rating: number
  check_in: string
  check_out: string
  location: GeoLocation
}

/** 单日餐饮安排 */
export interface DailyMeal {
  meal: string
  restaurant: string
  avg_price: number
  reason?: string
  rating?: number
  address?: string
  location?: GeoLocation
  coordinates?: GeoLocation
  longitude?: number
  latitude?: number
}

/** 每日行程 */
export interface DailyItinerary {
  day: number
  date: string
  date_label: string
  weather_summary?: string
  activities: DayActivity[]
  accommodation?: Accommodation
  meals?: DailyMeal[]
  day_cost: number
  day_summary: string
  // --- compat fields from SSE data ---
  attractions?: any[]
  hotel?: any
  traffic?: any[]
  title?: string
  theme?: string
}

/** 城际交通 */
export interface CityToCityTraffic {
  mode: string
  from: string
  to: string
  price: number
  duration: string
  recommendation?: string
}

/** 交通汇总 */
export interface TrafficSummary {
  city_to_city?: CityToCityTraffic[]
  city_internal?: string
  daily_traffic?: any[]
  daily_plan?: any[]
  summary?: string
  total_traffic_cost?: number
}

/** 推荐餐厅 */
export interface RecommendedRestaurant {
  name: string
  cuisine: string
  avg_price: number
  rating: number
  recommended_dishes: string[]
}

/** 美食汇总 */
export interface FoodSummary {
  recommended_restaurants?: RecommendedRestaurant[]
  total_food_budget?: number
  meal_plan?: any[]
  recommendations?: any[]
}

/** 预算项 */
export interface BudgetItem {
  name: string
  cost: number
}

/** 预算分类 */
export interface BudgetCategory {
  amount: number
  percent: number
  items: BudgetItem[]
}

/** 预算明细 */
export interface BudgetDetail {
  total: number
  breakdown?: Record<string, any>
  accommodation?: number
  food?: number
  attractions?: number
  traffic?: number
  shopping?: number
  other?: number
}

/** 纪念品推荐 */
export interface SouvenirRecommendation {
  name: string
  description: string
  estimated_price: string
  buy_place: string
}

/** 天气预报 */
export interface WeatherForecast {
  date: string
  weather: string
  temp_high: number
  temp_low: number
  wind: string
  humidity: number
  precipitation: number
  aqi: number
  advice: string
}

/**
 * 方案详情响应（后端 PlanResponse 映射）
 * PlanDetail 的别名，两者字段完全一致
 */
export type PlanResponse = PlanDetail

/** 完整方案详情 */
export interface PlanDetail {
  _id?: string
  id: string
  title: string
  destination: string
  departure: string
  start_date: string
  end_date: string
  days: number
  people_count: number
  crowd_type: string
  total_budget: number
  estimated_cost: number
  travel_style: string
  status: PlanStatus
  version: number
  is_favorite: boolean
  view_count: number
  overview: PlanOverview
  daily_itinerary: DailyItinerary[]
  traffic_summary: TrafficSummary
  food_summary: FoodSummary
  budget_detail: BudgetDetail
  souvenir_recommendations: SouvenirRecommendation[]
  weather_forecast: WeatherForecast[]
  packing_list: string[]
  tips: string[]
  avoid_list: string[]
  created_at: string
  updated_at: string
  // --- compat fields used by PlanPreview / SSE normalization ---
  pace?: string
  trip_config?: Record<string, any>
  traffic?: any
  hotel_plan?: any
  big_traffic?: any
  budget?: any
  meal_plan?: any[]
  attraction_details?: any[]
  food_details?: any[]
  is_saved?: boolean
  per_person_per_day?: number
  content_blocks?: any[]
}

/* ========== 方案生成/修改 ========== */

/** 触发方案生成请求 */
export interface GeneratePlanRequest {
  session_id: string
  confirmed: boolean
}

/** 修改操作类型 */
export type ModificationType = 'replace_activity' | 'remove_activity' | 'add_constraint'

/** 修改操作 */
export interface Modification {
  type: ModificationType
  day?: number
  activity_index?: number
  target_type?: ActivityType
  reason?: string
  constraints?: Record<string, unknown>
  constraint?: string
}

/** 修改方案请求 */
export interface ModifyPlanRequest {
  modifications: Modification[]
}

/** 重新生成请求 */
export interface RegeneratePlanRequest {
  session_id: string
  confirmed?: boolean
}

/* ========== 方案导出 ========== */

export type ExportFormat = 'md' | 'pdf' | 'image' | 'docx'

/** 导出任务响应 */
export interface ExportTaskResponse {
  task_id: string
  status: 'processing' | 'completed' | 'failed'
  estimated_wait_seconds?: number
  download_url?: string
  expires_at?: string
  error?: {
    code: number
    message: string
  }
}

/* ========== 方案分享 ========== */

/** 分享参数 */
export interface ShareOptions {
  expire_in?: number
  password?: string
}

/** 分享结果 */
export interface ShareResult {
  share_url: string
  expire_at?: string
}

/* ========== 方案从数据创建 ========== */

/** 从本地数据创建方案请求 */
export interface PlanFromDataRequest {
  title: string
  destination: string
  departure: string
  start_date: string
  end_date: string
  days: number
  budget: number
  estimated_cost: number
  travelers: number
  crowd_type: string
  travel_style: string
  preferences: string[]
  full_data: Record<string, any>
}

/* ========== 内容块类型（SSE 流式渲染） ========== */

export interface ContentBlockDayCard {
  day: number
  date: string
  date_label: string
  label: string
  weather_summary?: string
  activities: DayActivity[]
  accommodation?: Accommodation
  meals?: DailyMeal[]
  day_cost: number
  day_summary: string
  traffic?: any[]
}

export interface ContentBlockBudgetChart {
  total: number
  breakdown: Record<string, number>
}

export interface ContentBlockMap {
  markers: Array<{ position: [number, number]; title: string; content?: string; type?: string }>
  route_path?: Array<[number, number]>
}

export interface ContentBlockTrafficList {
  trains: any[]
  type?: string
}

export interface ContentBlockList {
  title?: string
  icon?: string
  items: string[]
}

export interface ContentBlock {
  type: 'header' | 'day_card' | 'budget_chart' | 'map' | 'traffic_list' | 'list' | 'weather' | 'packing' | 'tips' | 'avoid' | 'highlights' | 'section' | 'text' | 'divider' | 'callout'
  data: Record<string, unknown>
}

/* ========== 别名（兼容旧引用） ========== */

export type PlanModification = Modification
export type PlanExportTask = ExportTaskResponse
export type PlanShareResult = ShareResult
export type PlanFavoriteResult = { is_favorite: boolean }
export type Activity = DayActivity
