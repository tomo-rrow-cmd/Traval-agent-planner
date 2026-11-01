/* ============================================================
   用户偏好类型定义
   对应文档：API接口规范文档.md · §3.3
   ============================================================ */

/** 旅行风格 */
export type TravelStyle = 'relaxed' | 'balanced' | 'intensive' | 'food' | 'culture' | 'adventure'

/** 预算等级 */
export type BudgetLevel = 'budget' | 'cost_effective' | 'quality' | 'luxury'

/** 行程节奏 */
export type Pace = 'easy' | 'moderate' | 'packed'

/** 住宿偏好 */
export type AccommodationPref = 'hostel' | 'business' | 'boutique' | 'luxury'

/** 交通偏好 */
export type TransportPref = 'time_first' | 'cost_first' | 'comfort' | 'public' | 'self_drive'

/** AI 助手性格 */
export type AgentPersonality = 'friendly' | 'professional' | 'humorous' | 'lively'

/** 用户偏好配置 */
export interface UserPreferences {
  travel_style: TravelStyle
  budget_level: BudgetLevel
  pace: Pace
  diet_preferences: string[]
  food_taboos: string[]
  accommodation: AccommodationPref
  transport: TransportPref
  start_time: string
  end_time: string
  need_nap: boolean
  avoid_tags: string[]
  must_visit_places: string[]
  special_requests: string
  custom_agent_name: string
  agent_personality: AgentPersonality
}

/** 偏好默认值 */
export const DEFAULT_PREFERENCES: UserPreferences = {
  travel_style: 'relaxed',
  budget_level: 'cost_effective',
  pace: 'moderate',
  diet_preferences: [],
  food_taboos: [],
  accommodation: 'business',
  transport: 'time_first',
  start_time: '09:00',
  end_time: '21:00',
  need_nap: false,
  avoid_tags: [],
  must_visit_places: [],
  special_requests: '',
  custom_agent_name: '旅行者',
  agent_personality: 'friendly',
}
