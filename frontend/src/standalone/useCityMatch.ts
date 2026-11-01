import { computed, ref } from 'vue'
import type { City, CityMatch, CityScores, DimConfig, UserSelection } from './types'
import citiesData from './data/cities.json'

/** 14维度配置 */
export const DIM_CONFIGS: DimConfig[] = [
  { key: 'modern', label: '现代化', type: 'level', levels: ['传统', '中等', '现代'] },
  { key: 'nature', label: '自然风光', type: 'level', levels: ['基础', '中等', '丰富'] },
  { key: 'urban', label: '都市繁华', type: 'level', levels: ['安静', '中等', '繁华'] },
  { key: 'culture', label: '人文底蕴', type: 'level', levels: ['基础', '中等', '深厚'] },
  { key: 'sour', label: '酸', type: 'toggle' },
  { key: 'sweet', label: '甜', type: 'toggle' },
  { key: 'salty', label: '咸', type: 'toggle' },
  { key: 'spicy', label: '辣', type: 'toggle' },
  { key: 'summer', label: '夏天气候', type: 'single', levels: ['炎热', '适中', '凉爽'] },
  { key: 'scale', label: '城市规模', type: 'single', levels: ['小城', '中等', '大都市'] },
  { key: 'popular', label: '热门程度', type: 'single', levels: ['小众', '热门', '超热门'] },
  { key: 'mountain', label: '有名山', type: 'toggle' },
  { key: 'sea', label: '有海景', type: 'toggle' },
  { key: 'lake', label: '有湖泊', type: 'toggle' },
]

const BOOL_KEYS = new Set(['mountain', 'sea', 'lake'])
const ALL_KEYS = DIM_CONFIGS.map(d => d.key)
const cities: City[] = citiesData as City[]

/** 将 cities.json 本地路径转为可访问的 URL（如果项目里没有实际图片就用 null） */
function cityImage(c: City): string | null {
  return c.image ?? null
}

export function useCityMatch() {
  const selection = ref<UserSelection>({})

  /** 设置某个维度值（level/single类型用 value 0/1/2，toggle用 0 或 2，传 -1 取消） */
  function setDim(key: keyof CityScores, value: number) {
    const next = { ...selection.value }
    if (value < 0) {
      delete next[key]
    } else {
      next[key] = value
    }
    selection.value = next
  }

  /** 获取某个维度当前选择 */
  function getDim(key: keyof CityScores): number | undefined {
    return selection.value[key]
  }

  /** 编译用户选择为偏好描述文案 */
  const preferenceText = computed(() => {
    const parts: string[] = []
    for (const cfg of DIM_CONFIGS) {
      const v = selection.value[cfg.key]
      if (v === undefined) continue
      if (cfg.type === 'toggle') {
        parts.push(cfg.label)
      } else if (cfg.levels) {
        parts.push(`${cfg.label}${cfg.levels[v]}`)
      }
    }
    return parts.length > 0 ? parts.join('，') : '无偏好'
  })

  /** 实时匹配 Top 8 城市 */
  const topCities = computed<CityMatch[]>(() => {
    const sel = selection.value
    const touched = ALL_KEYS.filter(k => sel[k] !== undefined)

    if (touched.length === 0) {
      // 无偏好时按热门指数降序
      return [...cities]
        .sort((a, b) => b.scores.popular - a.scores.popular)
        .slice(0, 8)
        .map(c => ({
          name: c.name,
          tagline: c.tagline,
          match: Math.round((c.scores.popular / 2) * 100) / 100,
          image: cityImage(c),
        }))
    }

    // 计算最大曼哈顿距离
    let maxDist = 0
    for (const k of touched) {
      maxDist += BOOL_KEYS.has(k) ? 1 : 2
    }
    if (maxDist === 0) maxDist = 1

    const results: CityMatch[] = cities.map(c => {
      let dist = 0
      for (const k of touched) {
        dist += Math.abs((sel[k] ?? 0) - c.scores[k])
      }
      const sim = Math.max(0, Math.min(1, 1 - dist / maxDist))
      return {
        name: c.name,
        tagline: c.tagline,
        match: Math.round(sim * 100) / 100,
        image: cityImage(c),
      }
    })

    return results.sort((a, b) => b.match - a.match).slice(0, 8)
  })

  return { selection, setDim, getDim, topCities, preferenceText, DIM_CONFIGS }
}
