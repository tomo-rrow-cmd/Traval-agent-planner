/** 14维城市属性 */
export interface CityScores {
  modern: number
  nature: number
  urban: number
  culture: number
  sour: number
  sweet: number
  salty: number
  spicy: number
  summer: number
  scale: number
  popular: number
  mountain: number
  sea: number
  lake: number
}

export interface City {
  name: string
  tagline: string
  scores: CityScores
  image: string | null
  guide_url: string | null
}

/** 匹配结果 */
export interface CityMatch {
  name: string
  tagline: string
  match: number  // 0..1
  image: string | null
}

/** 维度配置 */
export type DimType = 'level' | 'single' | 'toggle'

export interface DimConfig {
  key: keyof CityScores
  label: string
  type: DimType
  levels?: string[]  // for 'level' and 'single' types
}

/** 用户选择：key -> 目标值 (undefined = 未选择) */
export type UserSelection = Partial<Record<keyof CityScores, number>>
