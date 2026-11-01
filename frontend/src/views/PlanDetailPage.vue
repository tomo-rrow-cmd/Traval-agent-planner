<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { usePlanStore } from '@/store/planStore'
import { useUiStore } from '@/store/uiStore'
import PlanTimeline from '@/components/plan/PlanTimeline.vue'
import BlockRenderer from '@/components/plan/BlockRenderer.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import ShareDialog from '@/components/plan/ShareDialog.vue'
import ExportDropdown from '@/components/plan/ExportDropdown.vue'
import WeatherForecast from '@/components/plan/WeatherForecast.vue'
import SouvenirList from '@/components/plan/SouvenirList.vue'
import BudgetOverviewCard from '@/components/plan/BudgetOverviewCard.vue'
import DayCard from '@/components/plan/DayCard.vue'
import { cleanDisplayText } from '@/components/plan/textFormat'
import { useTripStore } from '@/store/tripStore'
import { createPlanFromData } from '@/api/plan'
import { buildDailyMapData, type PlanMapMarker } from '@/utils/planMap'

const route = useRoute()
const router = useRouter()
const planStore = usePlanStore()
const uiStore = useUiStore()
const tripStore = useTripStore()

const planId = route.params.planId as string
const expandedDays = ref<number[]>([])
const loading = ref(true)
const shareDialogVisible = ref(false)
const useTestData = ref(false)
const isStartingTrip = ref(false)

onMounted(async () => {
  // 测试数据路由：按 planId 加载对应测试方案
  const testRoutes: Record<string, () => void> = {
    test: planStore.loadTestPlan,
    'test-chengdu': planStore.loadTestPlanChengdu,
    'test-beijing': planStore.loadTestPlanBeijing,
    test_qingdao: planStore.loadTestPlanQingdao,
    test_wuhan: planStore.loadTestPlanWuhan,
    test_xian: planStore.loadTestPlanXian,
  }
  const loadTest = testRoutes[planId]
  if (loadTest) {
    loadTest()
    useTestData.value = true
    loading.value = false
    return
  }

  // 如果已有方案数据（从SSE done事件来的），直接使用
  const cached = planStore.currentPlan
  const hasContent = cached && cached.days && (cached.daily_itinerary || []).some((d: any) => (d.activities || []).length > 0)
  if (hasContent) {
    // 如果 URL 是 'detail'（来自旧版 fallback），但 plan 有真实 id，则修正 URL
    const realId = cached.id || (cached as any)._id
    if ((planId === 'detail' || planId === '') && realId && realId !== 'detail') {
      router.replace(`/plans/${realId}`)
    }
    loading.value = false
    return
  }

  // 从缓存或 API 获取
  if (planId && planId !== 'detail') {
    try {
      await planStore.fetchPlanDetail(planId)
    } catch {
      useTestData.value = true
    }
  }
  loading.value = false
})

const plan = computed(() => planStore.currentPlan)

const BUDGET_CATEGORIES: Record<string, string> = {
  '住宿': 'accommodation', accommodation: 'accommodation', hotel: 'accommodation',
  '交通': 'transport', transport: 'transport', traffic: 'transport',
  '餐饮': 'food', '美食': 'food', food: 'food', meal: 'food',
  '门票': 'attractions', '景点': 'attractions', attractions: 'attractions', ticket: 'attractions',
  '购物': 'souvenirs', '纪念品': 'souvenirs', souvenirs: 'souvenirs', shopping: 'souvenirs',
  '备用': 'contingency', contingency: 'contingency', other: 'contingency',
}

const budgetOverview = computed(() => {
  const current = plan.value as any
  if (!current) return null

  const rawBudget = current.budget || {}
  const structuredBudget = current.budget_detail || {}
  const total = Number(rawBudget.total_budget || structuredBudget.total || current.total_budget) || 0
  const estimated = Number(rawBudget.actual_total || current.estimated_cost) || 0
  const rawDetails = Array.isArray(rawBudget.details) ? rawBudget.details : []
  const breakdown: Record<string, any> = { ...(structuredBudget.breakdown || {}) }

  for (const detail of rawDetails) {
    const key = BUDGET_CATEGORIES[String(detail.category || '').toLowerCase()]
    if (!key) continue
    const amount = Number(detail.spent) || 0
    breakdown[key] = {
      amount,
      percent: total > 0 ? Math.round(amount / total * 100) : 0,
      items: [],
    }
  }

  if (!total && !estimated && !rawDetails.length && !Object.keys(breakdown).length) return null

  const suggestions = (rawBudget.suggestions || []).map((suggestion: any) => {
    if (typeof suggestion === 'string') return suggestion
    return `${suggestion.action || ''}${suggestion.save ? `（可省 ¥${suggestion.save}）` : ''}`
  }).filter(Boolean)

  return {
    total,
    estimated,
    breakdown,
    details: rawDetails.map((detail: any) => ({
      category: detail.category || '其他',
      budget: Number(detail.budget) || 0,
      spent: Number(detail.spent) || 0,
      status: detail.status || 'ok',
    })),
    warnings: (rawBudget.warnings || []).filter(Boolean),
    suggestions,
  }
})

/** 有效 planId：优先用 plan 自身的 id，其次 route param */
const effectivePlanId = computed(() => plan.value?.id || (plan.value as any)?._id || planId)

async function handleStartTrip() {
  const id = effectivePlanId.value
  if (!id || id === 'detail' || id === 'test' || id === 'test-chengdu' || id === 'test-beijing' || id === '') {
    uiStore.showError('方案尚未保存，请先保存方案')
    return
  }
  isStartingTrip.value = true
  try {
    const isLocalId = typeof id === 'string' && (id.startsWith('local_') || id === 'test_plan_001')
    const trip = await tripStore.beginTrip(id, isLocalId ? (plan.value ?? undefined) : undefined)
    if (trip?.id) {
      router.push(`/trips/${trip.id}`)
    } else {
      uiStore.showError('创建行程失败')
    }
  } catch {
    uiStore.showError('创建行程失败，请检查后端服务')
  } finally {
    isStartingTrip.value = false
  }
}

// 如果 plan 更新了但 URL 还是 detail，修正 URL
watch(plan, (p) => {
  if (!p) return
  const realId = p.id || (p as any)._id
  if ((planId === 'detail' || planId === '') && realId && realId !== 'detail') {
    router.replace(`/plans/${realId}`)
  }
}, { immediate: true })

/** 后备：将 daily_itinerary 转为 day_card 块（字段名兼容转换） */
const dailyBlocks = computed(() => {
  const itinerary = plan.value?.daily_itinerary
  if (!itinerary || !itinerary.length) return []

  const blocks: any[] = []

  // Header 块
  blocks.push({
    type: 'header',
    data: {
      days: plan.value?.days,
      title: plan.value?.title,
      origin: plan.value?.departure,
      destination: plan.value?.destination,
      pace: (plan.value as any)?.pace || '适中',
      traveler_count: plan.value?.people_count || 1,
      total_budget: plan.value?.total_budget || 0,
      estimated_cost: plan.value?.estimated_cost || 0,
    },
  })

  // 概览统计（总里程 / 交通方式 / 适合人群）
  const overview = plan.value?.overview
  const hasStats = overview && (overview.total_distance_km > 0 || overview.transport_modes.length > 0 || plan.value?.crowd_type)
  const hasHighlights = overview?.highlights && overview.highlights.length > 0
  if (hasHighlights || hasStats) {
    const hItems = (overview?.highlights || []).map((h: string) => ({ emoji: '✨', text: h }))
    blocks.push({
      type: 'highlights',
      data: {
        items: hItems,
        total_distance_km: overview?.total_distance_km || 0,
        transport_modes: overview?.transport_modes || [],
        crowd_type: plan.value?.crowd_type || '',
        people_count: plan.value?.people_count || 1,
      },
    })
    if (hasStats) {
      const statParts: string[] = []
      if (overview?.total_distance_km) statParts.push(`总里程约 ${overview.total_distance_km} km`)
      if (overview?.transport_modes?.length) statParts.push(`交通: ${overview.transport_modes.join('/')}`)
      if (plan.value?.crowd_type) statParts.push(`适合 ${(plan.value as any).crowd_type}`)
      if (statParts.length) {
        blocks.push({
          type: 'text',
          data: { content: `📊 **行程概览** · ${statParts.join(' · ')}` },
        })
      }
    }
  }

  // DayCard 块（兼容新旧字段名）
  const forecasts = plan.value?.weather_forecast || []
  const mealPlan = (plan.value as any)?.meal_plan || []
  const hotelPlan = (plan.value as any)?.hotel_plan || {}
  const hotelRecommendations = hotelPlan.recommendations || []
  const selectedHotel = hotelPlan.selected_hotel
    || hotelRecommendations.find((hotel: any) => hotel.name === hotelPlan.selected)
    || (hotelRecommendations.length === 1 ? hotelRecommendations[0] : undefined)
  const selectedHotelNights = selectedHotel
    ? (Number(selectedHotel.nights) || Math.max(itinerary.length - 1, 0))
    : 0

  // 天气预报回退：weather_forecast 为空时从每日 weather_summary 提取
  if (forecasts.length === 0 && itinerary.some((d: any) => d.weather_summary)) {
    blocks.push({ type: 'divider', data: {} })
    blocks.push({ type: 'section', data: { icon: 'sun', title: '天气预报' } })
    for (const d of itinerary) {
      if (d.weather_summary) {
        blocks.push({ type: 'text', data: { content: `第${d.day}天：${d.weather_summary}` } })
      }
    }
  }

  itinerary.forEach((day: any, i: number) => {
    const rawActs = day.activities || day.attractions || []
    const forecast = forecasts[i]
    blocks.push({
      type: 'day_card',
      data: {
        day: day.day,
        date: day.date || '',
        date_label: day.date_label || '',
        label: day.date_label || '',
        weather_summary: day.weather_summary || '',
        day_cost: day.day_cost || 0,
        day_summary: day.day_summary || '',
        _forecast: forecast ? {
          weather: forecast.weather,
          temp_high: forecast.temp_high,
          temp_low: forecast.temp_low,
          advice: forecast.advice,
        } : undefined,
        activities: rawActs.map((a: any) => ({
          time_slot: a.time_slot || '',
          type: a.type || 'attraction',
          title: a.title || a.name || '',
          subtitle: a.subtitle || '',
          description: a.description || a.reason || '',
          cost: a.cost ?? a.price ?? 0,
          duration_minutes: a.duration_minutes || (a.duration_hours ? Math.round(a.duration_hours * 60) : undefined),
          rating: a.rating || 0,
          tags: a.tags || [],
          tips: a.tips || '',
          location: a.location || (a.latitude && a.longitude ? { lat: a.latitude, lng: a.longitude } : undefined),
        })),
        accommodation: (() => {
          const h = (day as any).accommodation
            || (day as any).hotel
            || (i < selectedHotelNights ? selectedHotel : undefined)
          return h ? {
            hotel_name: cleanDisplayText(h.hotel_name || h.name),
            address: cleanDisplayText(h.address),
            price: h.price || h.price_per_night || (h.total && selectedHotelNights ? h.total / selectedHotelNights : 0),
            rating: h.rating || 0,
            room_type: h.room_type || '',
            check_in: h.check_in || '',
            check_out: h.check_out || '',
            location: h.location || (h.latitude != null && h.longitude != null ? { lat: h.latitude, lng: h.longitude } : undefined),
          } : undefined
        })(),
        meals: day.meals?.length
          ? day.meals
          : (mealPlan.find((mealDay: any) => Number(mealDay.day) === Number(day.day))?.meals || []),
      },
    })
  })

  // ----- 推荐车次（后备：从 big_traffic 提取） -----
  const rawBt = (plan.value as any)?.big_traffic
  const trafficGroups = Array.isArray(rawBt) ? rawBt : (rawBt ? [rawBt] : [])
  const trains = trafficGroups.flatMap((group: any) => {
    if (Array.isArray(group?.trains)) return group.trains
    return group?.trainCode ? [group] : []
  })
  const returnTrains = trafficGroups.flatMap((group: any) => group?.return_trains || [])
  if (trains.length) {
    blocks.push({ type: 'divider', data: {} })
    blocks.push({ type: 'section', data: { icon: 'train', title: '推荐车次', subtitle: `${plan.value?.departure || ''} → ${plan.value?.destination || ''}` } })
    blocks.push({ type: 'traffic_list', data: { trains: trains.slice(0, 6) } })
  }
  if (returnTrains.length) {
    blocks.push({ type: 'divider', data: {} })
    blocks.push({ type: 'section', data: { icon: 'train', title: '返程推荐', subtitle: `${plan.value?.destination || ''} → ${plan.value?.departure || ''}` } })
    blocks.push({ type: 'traffic_list', data: { trains: returnTrains.slice(0, 6) } })
  }

  // ----- 市内交通（后备：从 traffic 提取） -----
  const rawTraffic = (plan.value as any)?.traffic
  if (rawTraffic?.daily_traffic?.length || rawTraffic?.summary || rawTraffic?.time_warnings?.length) {
    blocks.push({ type: 'divider', data: {} })
    if (rawTraffic.daily_traffic?.length) {
      const traffic = rawTraffic.daily_traffic
      const segments = traffic.flatMap((dayTraffic: any) => dayTraffic.segments || [])
      const modeNames: Record<string, string> = { transit: '公共交通', subway: '地铁', walking: '步行', driving: '打车', taxi: '打车', bus: '公交', bike: '骑行' }
      const modes = Array.from(new Set(segments.map((segment: any) => {
        const mode = String(segment.mode || '').replace('(est)', '')
        return modeNames[mode] || mode
      }).filter(Boolean)))
      const totalTime = traffic.reduce((sum: number, dayTraffic: any) => sum + (Number(dayTraffic.total_time_min) || 0), 0)
      const totalCost = traffic.reduce((sum: number, dayTraffic: any) => sum + (Number(dayTraffic.total_cost) || 0), 0)
      const duration = `${Math.floor(totalTime / 60)}h${totalTime % 60}min`
      const subtitleParts = [`${traffic.length}天`, `共${segments.length}段`, duration, `¥${totalCost}`]
      if (modes.length) subtitleParts.splice(2, 0, modes.slice(0, 3).join('/'))
      blocks.push({ type: 'section', data: { icon: 'tip', title: '市内交通概览', subtitle: subtitleParts.join(' · ') } })
      const tableHeader = '| 日期 | 时间 | 费用 |\n|------|------|------|'
      const tableRows = traffic.map((d: any) =>
        `| D${d.day} | ${Math.floor((d.total_time_min || 0) / 60)}h${(d.total_time_min || 0) % 60}min | ¥${d.total_cost || 0} |`
      ).join('\n')
      blocks.push({
        type: 'text',
        data: { content: `**每日汇总**\n\n${tableHeader}\n${tableRows}\n| **合计** | **${duration}** | **¥${totalCost}** |` },
      })
    } else {
      blocks.push({ type: 'section', data: { icon: 'tip', title: '市内交通概览' } })
    }
    if (rawTraffic.summary) {
      blocks.push({ type: 'callout', data: { icon: 'tip', level: 'info', title: '出行建议', text: rawTraffic.summary } })
    }
    if (rawTraffic.time_warnings?.length) {
      blocks.push({ type: 'callout', data: { icon: 'warning', level: 'warning', title: '时间提醒', text: rawTraffic.time_warnings?.slice(0, 3).join('；') || '' } })
    }
  }

  return blocks
})

const testBlocks = computed(() => {
  if (!useTestData.value) return []
  return getTestContentBlocks()
})

const contentBlocks = computed(() => {
  if ((plan.value as any)?.content_blocks?.length) {
    return (plan.value as any).content_blocks
  }
  if (testBlocks.value.length) {
    return testBlocks.value
  }
  return dailyBlocks.value
})

const summaryBlocks = computed(() => {
  const result: any[] = []
  let skippingBudgetSection = false
  for (const block of contentBlocks.value as any[]) {
    if (block.type === 'header' || block.type === 'day_card' || block.type === 'map') continue
    if (block.type === 'section' && /预算/.test(block.data?.title || '')) {
      skippingBudgetSection = true
      if (result.at(-1)?.type === 'divider') result.pop()
      continue
    }
    if (block.type === 'budget_chart') {
      if (result.at(-1)?.type === 'divider') result.pop()
      continue
    }
    if (skippingBudgetSection) {
      if (block.type === 'divider') skippingBudgetSection = false
      continue
    }
    result.push(block)
  }
  return result
})
const dayCardBlocks = computed(() => contentBlocks.value.filter((b: any) => b.type === 'day_card') as any[])

/**
 * 为每一天生成地图标记和完整路线（酒店→活动→酒店）
 */
const dayMarkersMap = computed(() => {
  const map = new Map<number, {
    markers: PlanMapMarker[]
    routePath: Array<[number, number]>
    centerPoint: [number, number]
  }>()
  const dayCards = dayCardBlocks.value
  for (const block of dayCards) {
    const day = block.data.day
    const mealPlan = (plan.value as any)?.meal_plan || []
    const meals = block.data.meals?.length
      ? block.data.meals
      : (mealPlan.find((mealDay: any) => Number(mealDay.day) === Number(day))?.meals || [])
    const hotelPlan = (plan.value as any)?.hotel_plan || {}
    const recommendations = hotelPlan.recommendations || []
    const selectedHotel = hotelPlan.selected_hotel
      || recommendations.find((hotel: any) => hotel.name === hotelPlan.selected)
      || recommendations[0]
    const mapData = buildDailyMapData({ ...block.data, meals }, selectedHotel)

    map.set(day, mapData)
  }
  return map
})

function toggleDay(day: number) {
  if (expandedDays.value.includes(day)) {
    expandedDays.value = expandedDays.value.filter(d => d !== day)
  } else {
    expandedDays.value = [...expandedDays.value, day]
  }
}

function handleBack() {
  router.back()
}

async function handleSave() {
  const p = plan.value
  if (!p) { uiStore.showError('无方案数据'); return }

  // 已保存到后端的不重复调用
  if ((p as any)._persisted) { uiStore.showSuccess('方案已保存'); return }

  try {
    const payload = {
      title: p.title || '未命名旅行方案',
      destination: p.destination || '',
      departure: p.departure || '',
      start_date: p.start_date || '',
      end_date: p.end_date || '',
      days: p.days || 0,
      budget: p.total_budget || 0,
      estimated_cost: p.estimated_cost || 0,
      travelers: p.people_count || 1,
      crowd_type: p.crowd_type || '',
      travel_style: p.travel_style || '',
      preferences: [],
      full_data: JSON.parse(JSON.stringify(p)),
    }
    const res = await createPlanFromData(payload)
    const savedPlan = res.data?.data
    if (savedPlan?.id) {
      // 用后端的真实 ID 替换本地 ID，使导出等功能可用
      planStore.currentPlan = { ...p, id: savedPlan.id, _persisted: true } as any
      // URL 替换为真实 ID
      router.replace(`/plans/${savedPlan.id}`)
    }
    uiStore.showSuccess('方案已保存到我的方案')
  } catch (e: any) {
    uiStore.showError(e?.response?.data?.message || e.message || '保存失败，请稍后重试')
  }
}

async function handleFavorite() {
  try {
    await planStore.toggleFavorite(effectivePlanId.value)
    uiStore.showSuccess(plan.value?.is_favorite ? '已收藏' : '已取消收藏')
  } catch {
    uiStore.showError('操作失败')
  }
}

function handleShare() {
  shareDialogVisible.value = true
}

async function handleExport(format: string) {
  // 只有 Markdown 由父组件客户端生成，其余格式由 ExportDropdown 自行处理
  if (format !== 'md') return

  const p = plan.value
  if (!p) { uiStore.showError('无方案数据'); return }
  try {
    const md = generateClientMarkdown(p)
    const blob = new Blob([md], { type: 'text/markdown;charset=utf-8' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${p.title || 'travel_plan'}.md`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
    uiStore.showSuccess('Markdown 已下载')
  } catch {
    uiStore.showError('Markdown 导出失败')
  }
}

/** 客户端生成 Markdown（不依赖后端） */
function generateClientMarkdown(p: any): string {
  const lines: string[] = []

  // 标题
  lines.push(`# 🗺️ ${p.title || p.trip_name || '旅行方案'}`)
  const route = [p.departure, p.destination].filter(Boolean).join(' → ')
  if (route) lines.push(`**${route}** · **${p.days}天**`)
  lines.push('')

  // 概览
  if (p.overview?.highlights?.length) {
    lines.push('## ✨ 行程亮点')
    p.overview.highlights.forEach((h: string) => lines.push(`- ${h}`))
    lines.push('')
  }

  // 每日行程
  const itinerary = p.daily_itinerary || []
  for (const day of itinerary) {
    const dn = day.day || 1
    const dateStr = day.date ? `（${day.date}）` : ''
    const weather = day.weather_summary ? ` ${day.weather_summary}` : ''
    lines.push(`## 📅 第${dn}天${dateStr}${weather}`)
    if (day.day_summary) lines.push(`> ${day.day_summary}`)
    lines.push('')

    const acts = day.activities || day.attractions || []
    for (const a of acts) {
      lines.push(`### ${a.title || a.name}`)
      if (a.description || a.reason) lines.push(`> ${a.description || a.reason}`)
      const tags: string[] = []
      if (a.duration_hours || a.duration_minutes) {
        const min = a.duration_minutes || (a.duration_hours * 60)
        tags.push(`⏱ ${Math.floor(min / 60)}h${min % 60}min`)
      }
      if (a.cost !== undefined || a.price !== undefined) {
        const cost = a.cost ?? a.price
        tags.push(cost === 0 ? '免费' : `¥${cost}`)
      }
      if (a.rating) tags.push(`⭐ ${a.rating}`)
      if (a.tips) tags.push(`💡 ${Array.isArray(a.tips) ? a.tips.join('；') : a.tips}`)
      if (tags.length) lines.push(`> \`${tags.join('` `')}\``)
      lines.push('')
    }

    // 餐饮
    const meals = day.meals || []
    for (const m of meals) {
      let line = `🍽 **${m.meal || '餐饮'}**`
      if (m.restaurant) line += `：${m.restaurant}`
      if (m.avg_price || m.cost) line += ` ¥${m.avg_price || m.cost}`
      if (m.reason || m.description) line += ` — ${m.reason || m.description}`
      lines.push(line)
    }
    if (meals.length) lines.push('')

    // 住宿
    const hotel = day.accommodation || day.hotel
    if (hotel) {
      let line = `🏨 ${hotel.hotel_name || hotel.name || '住宿'}`
      if (hotel.price || hotel.price_per_night) line += ` ¥${hotel.price || hotel.price_per_night}/晚`
      if (hotel.address) line += `（${hotel.address}）`
      lines.push(line)
      lines.push('')
    }
  }

  // 预算
  const budget = p.budget || p.budget_detail
  if (budget) {
    lines.push('## 💰 预算')
    if (budget.total_budget || budget.total) lines.push(`总预算：¥${budget.total_budget || budget.total}`)
    if (budget.actual_total || budget.estimated_cost) lines.push(`预估花费：¥${budget.actual_total || budget.estimated_cost}`)
    if (budget.details?.length) {
      lines.push('')
      lines.push('| 分类 | 预算 | 花费 |')
      lines.push('|------|------|------|')
      for (const d of budget.details) {
        lines.push(`| ${d.category} | ¥${d.budget || 0} | ¥${d.spent || 0} |`)
      }
    }
    lines.push('')
  }

  // Tips
  if (p.tips?.length) {
    lines.push('## 💡 出行建议')
    p.tips.forEach((t: string) => lines.push(`- ${t}`))
    lines.push('')
  }

  // 避坑
  if (p.avoid_list?.length) {
    lines.push('## ⚠️ 避坑提醒')
    p.avoid_list.forEach((a: string) => lines.push(`- ${a}`))
    lines.push('')
  }

  return lines.join('\n')
}

function getTestContentBlocks() {
  return [
    { type: 'text', data: { content: '**行程总览**：广州 → 长沙，7日深度游，适合朋友/情侣出行。节奏张弛有度，涵盖历史、美食、文艺与自然风光。' } },
    { type: 'day_card', data: { day:1, date:'2026-07-10', label:'周五', weather_summary:'☀️ 32°C', day_cost:315, day_summary:'从千年学府到湘江中心。', activities:[
      { time_slot:'09:00-12:00', type:'attraction', title:'岳麓山', subtitle:'南大门上东大门下', description:'长沙地标，海拔300米。先参观岳麓书院，登顶俯瞰湘江全景。', cost:0, duration_minutes:180, rating:4.7, tags:['文化','必去'], tips:'建议南大门上东大门下', location:{lng:112.947,lat:28.193} },
      { time_slot:'14:00-17:00', type:'attraction', title:'橘子洲', subtitle:'毛泽东青年艺术雕塑', description:'湘江中心岛屿。毛泽东雕塑高32米。可乘小火车(¥20)往返，傍晚拍照最佳。', cost:0, duration_minutes:120, rating:4.5, tags:['经典','拍照'], tips:'傍晚前往光线最佳', location:{lng:112.960,lat:28.175} },
      { time_slot:'18:00-21:00', type:'food', title:'太平老街', subtitle:'最有烟火气的老街', description:'汇集黑色经典臭豆腐、糖油粑粑等标志性小吃。', cost:60, duration_minutes:120, rating:4.6, tags:['美食','夜景'], tips:'臭豆腐推荐黑色经典', location:{lng:112.978,lat:28.197} },
    ], accommodation:{hotel_name:'匠宿酒店(五一广场)', address:'芙蓉区五一广场', price:400, rating:4.7, location:{lng:112.979,lat:28.195}} } },
    { type: 'day_card', data: { day:2, date:'2026-07-11', label:'周六', weather_summary:'⛅ 30°C', day_cost:432, day_summary:'深入文化内核。', activities:[
      { time_slot:'09:00-12:00', type:'attraction', title:'湖南省博物馆', subtitle:'马王堆汉墓', description:'最大看点辛追夫人遗体(2100年不腐)、素纱襌衣(49克)。免费需预约，周一闭馆。', cost:0, duration_minutes:180, rating:4.9, tags:['文化','必去'], tips:'提前3天公众号预约', location:{lng:113.004,lat:28.209} },
      { time_slot:'13:00-15:00', type:'attraction', title:'天心阁', subtitle:'古城标志', description:'明代始建，登顶俯瞰古城风貌。', cost:32, duration_minutes:90, rating:4.2, tags:['历史'], location:{lng:112.982,lat:28.186} },
      { time_slot:'17:00-20:00', type:'food', title:'坡子街', subtitle:'火宫殿所在地', description:'火宫殿(260年历史)聚集长沙最全小吃。', cost:120, duration_minutes:150, rating:4.5, tags:['美食','夜市'], tips:'火宫殿人均¥60-80', location:{lng:112.976,lat:28.191} },
    ], accommodation:{hotel_name:'匠宿酒店(五一广场)', price:400, rating:4.7, location:{lng:112.979,lat:28.195}} } },
    { type: 'day_card', data: { day:3, date:'2026-07-12', label:'周日', weather_summary:'🌦️ 28°C', day_cost:280, day_summary:'自然与艺术碰撞。', activities:[
      { time_slot:'09:00-11:30', type:'attraction', title:'湖南省植物园', subtitle:'城市森林氧吧', description:'140公顷城市森林氧吧。夏季绿树成荫适合拍照。', cost:20, duration_minutes:150, rating:4.3, tags:['自然'], tips:'带驱蚊水', location:{lng:113.028,lat:28.118} },
      { time_slot:'14:00-16:00', type:'attraction', title:'梅溪湖文化艺术中心', subtitle:'扎哈哈迪德遗作', description:'三朵芙蓉花造型建筑。外围散步拍照也值。', cost:0, duration_minutes:90, rating:4.6, tags:['建筑','打卡'], location:{lng:112.897,lat:28.193} },
      { time_slot:'17:00-19:00', type:'shopping', title:'万家丽国际MALL', subtitle:'亚洲最大单体建筑', description:'顶层空中花园俯瞰天际线，日落绝佳。', cost:80, duration_minutes:120, rating:4.1, tags:['逛街'], tips:'日落约18:30', location:{lng:113.035,lat:28.195} },
    ], accommodation:{hotel_name:'匠宿酒店(五一广场)', price:400, rating:4.7, location:{lng:112.979,lat:28.195}} } },
    { type: 'day_card', data: { day:4, date:'2026-07-13', label:'周一', weather_summary:'⛅ 31°C', day_cost:356, day_summary:'文艺打卡日。', activities:[
      { time_slot:'10:00-12:00', type:'attraction', title:'潮宗街', subtitle:'长沙宽窄巷子', description:'清末民初建筑群，文创小店林立。', cost:0, duration_minutes:120, rating:4.4, tags:['文艺'], location:{lng:112.973,lat:28.200} },
      { time_slot:'14:00-16:00', type:'rest', title:'止间书店', subtitle:'长沙最美书店', description:'大学城人文书店，空间极具格调。', cost:35, duration_minutes:120, rating:4.5, tags:['书店'], location:{lng:112.946,lat:28.184} },
      { time_slot:'18:30-21:00', type:'entertainment', title:'湘江夜游', subtitle:'乘游船赏夜景', description:'游船沿湘江航行，两岸灯光秀。', cost:100, duration_minutes:120, rating:4.6, tags:['夜景'], tips:'提前美团购票¥80', location:{lng:112.970,lat:28.179} },
    ], accommodation:{hotel_name:'匠宿酒店(五一广场)', price:400, rating:4.7, location:{lng:112.979,lat:28.195}} } },
    { type: 'day_card', data: { day:5, date:'2026-07-14', label:'周二', weather_summary:'☀️ 33°C', day_cost:512, day_summary:'美食探索日。', activities:[
      { time_slot:'07:00-09:00', type:'food', title:'南门口早市', subtitle:'老长沙早餐', description:'公交新村粉店(牛肉粉¥16)、糖油佗佗。', cost:30, duration_minutes:120, rating:4.5, tags:['美食'], location:{lng:112.982,lat:28.186} },
      { time_slot:'12:30-14:00', type:'food', title:'费大厨辣椒炒肉', subtitle:'必吃榜第一名', description:'招牌辣椒炒肉¥68，人均¥70。', cost:140, duration_minutes:90, rating:4.7, tags:['湘菜'], tips:'11点前去取号', location:{lng:112.981,lat:28.193} },
    ], accommodation:{hotel_name:'匠宿酒店(五一广场)', price:400, rating:4.7, location:{lng:112.979,lat:28.195}} } },
    { type: 'day_card', data: { day:6, date:'2026-07-15', label:'周三', weather_summary:'☀️ 34°C', day_cost:420, day_summary:'主题乐园日。', activities:[
      { time_slot:'09:30-17:00', type:'entertainment', title:'方特东方神画', subtitle:'文化主题乐园', description:'女娲补天(4D过山车)、牛郎织女。', cost:280, duration_minutes:420, rating:4.5, tags:['乐园'], tips:'下载方特APP看排队', location:{lng:112.812,lat:28.117} },
      { time_slot:'18:30-20:00', type:'food', title:'四方坪夜市', subtitle:'本地人最爱', description:'李记飞饼、烤猪蹄，人均¥50。', cost:100, duration_minutes:90, rating:4.6, tags:['夜市'], location:{lng:113.012,lat:28.224} },
    ], accommodation:{hotel_name:'梅溪湖金茂豪华精选酒店', price:650, rating:4.8, location:{lng:112.898,lat:28.194}} } },
    { type: 'day_card', data: { day:7, date:'2026-07-16', label:'周四', weather_summary:'⛅ 30°C', day_cost:287, day_summary:'收尾返程。', activities:[
      { time_slot:'09:00-11:00', type:'shopping', title:'黄兴路步行街', subtitle:'采购伴手礼', description:'品牌旗舰店+特色小吃+文创集市。', cost:200, duration_minutes:120, rating:4.2, tags:['购物'], location:{lng:112.979,lat:28.192} },
      { time_slot:'12:00-13:30', type:'food', title:'一盏灯长沙菜', subtitle:'地道湘菜', description:'酸萝卜炒肚丝、鸭掌筋。人均¥65。', cost:130, duration_minutes:90, rating:4.6, tags:['湘菜'], tips:'不能吃辣说微辣', location:{lng:112.980,lat:28.190} },
      { time_slot:'14:30-16:00', type:'transport', title:'长沙南站返程', subtitle:'高铁回广州', description:'高铁约2.5-3小时，提前1小时到站。', cost:628, duration_minutes:180, tags:['交通'], location:{lng:113.059,lat:28.145} },
    ] } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon: 'train', title: '城际交通推荐', subtitle: '广州南-长沙南，高铁2.5-3h，二等座¥314' } },
    { type: 'traffic_list', data: { trains: [
      { trainCode:'G6102', fromStationName:'广州南', toStationName:'长沙南', departureTime:'08:30', arrivalTime:'11:00', duration:'2h30m', prices:{'二等座':314,'一等座':504,'商务座':998} },
      { trainCode:'G6112', fromStationName:'广州南', toStationName:'长沙南', departureTime:'09:15', arrivalTime:'12:45', duration:'3h30m', prices:{'二等座':314,'一等座':504} },
      { trainCode:'G6028', fromStationName:'广州南', toStationName:'长沙南', departureTime:'14:30', arrivalTime:'17:55', duration:'3h25m', prices:{'二等座':299,'一等座':478} },
    ] } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon: 'tip', title: '市内交通指引', subtitle: '地铁覆盖95%景点' } },
    { type: 'text', data: { content: '🚇 **地铁**：6条线路覆盖主要景点，微信/支付宝扫码乘车。3日票¥40不限次。\n\n🚕 **打车**：起步价¥8，景区间¥15-30。高峰期避开五一广场周边。\n\n🚲 **共享单车**：美团/哈啰单车遍布全城，适合短距离接驳。\n\n**每日交通建议**\n- D1 岳麓山→橘子洲：地铁2号线+步行\n- D2 省博→天心阁：打车约¥18\n- D3 植物园→梅溪湖：公交370路直达\n- D4 潮宗街→止间书店：步行10分钟\n- D6 方特：建议全程打车约¥40单程' } },
    { type: 'text', data: { content: '### 🚖 每日交通费用\n\n| 日期 | 时间 | 费用 |\n|------|------|------|\n| D1（07/10） | 1h08min | ¥16 |\n| D2（07/11） | 52min | ¥22 |\n| D3（07/12） | 1h28min | ¥24 |\n| D4（07/13） | 1h25min | ¥18 |\n| D5（07/14） | 1h30min | ¥30 |\n| D6（07/15） | 1h15min | ¥68 |\n| D7（07/16） | 55min | ¥6 |\n| **合计** | | **¥184** |\n\n> 全程交通费用 ¥184，占预算 3.7%，以地铁和步行为主，D6 方特打车拉高单日费用。' } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon: 'tip', title: '住宿方案对比' } },
    { type: 'text', data: { content: '**方案A（推荐）匠宿酒店·五一广场店**\n评分 4.7 ⭐ | ¥400/晚\n市中心核心位置，步行可达太平街/坡子街，地铁口步行3分钟。\n\n**方案B 梅溪湖金茂豪华精选酒店**\n评分 4.8 ⭐ | ¥650/晚\n梅溪湖畔湖景房，毗邻文化艺术中心，适合文艺爱好者。\n\n**方案C 长沙瑞吉酒店**\n评分 4.9 ⭐ | ¥1,200/晚\nIFS国金中心高空景观，顶层酒吧俯瞰长沙天际线，奢华之选。' } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon: 'info', title: '预算分析', subtitle: '总预算¥5000 预估¥4652 剩余¥348' } },
    { type: 'budget_chart', data: { total:5000, breakdown:{transport:942, accommodation:2650, food:910, attractions:432, souvenirs:200, contingency:500} } },
    { type: 'callout', data: { icon:'warning', level:'warning', title:'住宿超预算', text:'住宿¥2650(53%)超建议占比35%。建议降至¥400内' } },
    { type: 'callout', data: { icon:'tip', level:'success', title:'省钱建议', text:'核心景点多免费 餐饮¥910控制合理 提前美团购游船票¥80' } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon: 'landmark', title: '景点深度攻略', subtitle: '精选景点细节' } },
    { type: 'callout', data: { icon:'landmark', level:'info', title:'岳麓山路线', text:'南大门进-岳麓书院(¥40)-爱晚亭-穿石坡湖-东大门出。全程约3h，下山滑道¥35' } },
    { type: 'callout', data: { icon:'landmark', level:'info', title:'省博参观贴士', text:'免费需预约！公众号提前3天。周一闭馆。禁止闪光灯。' } },
    { type: 'callout', data: { icon:'landmark', level:'info', title:'方特攻略', text:'开园09:30-17:30。必玩：女娲补天、牛郎织女。下载方特APP看排队。' } },
    { type: 'divider', data: {} },
    { type: 'list', data: { title:'行李清单', description:'逐项核对', items:['身份证','手机+充电器+充电宝','防晒霜SPF50+','遮阳帽','便携风扇','肠胃药','雨伞','步行鞋','换洗衣物3-4套','洗漱用品','学生证'] } },
    { type: 'divider', data: {} },
    { type: 'section', data: { icon: 'tip', title: '避坑提醒' } },
    { type: 'callout', data: { icon:'warning', level:'warning', text:'不要信司机推荐的便宜一日游，都是购物团' } },
    { type: 'callout', data: { icon:'warning', level:'warning', text:'太平街水果捞¥30+不推荐' } },
    { type: 'callout', data: { icon:'warning', level:'warning', text:'雨季湘江游船可能停航，出发前确认' } },
    { type: 'callout', data: { icon:'warning', level:'warning', text:'方特附近黑车要价高，建议打车或公交' } },
  ]
}
</script>

<template>
  <div
    v-if="!loading && (plan || contentBlocks.length)"
    id="plan-detail-content"
    class="plan-detail-page"
  >
    <!-- 工具栏：导出按钮放标题上方 -->
    <div class="plan-detail-page__toolbar">
      <a-button
        class="plan-detail-page__back-btn"
        @click="handleBack"
      >
        ← 返回对话
      </a-button>
      <div class="plan-detail-page__toolbar-right">
        <ExportDropdown
          :plan-id="effectivePlanId"
          @export="handleExport"
        />
        <a-button
          type="primary"
          class="plan-detail-page__save-btn"
          :disabled="!!plan?.is_saved"
          @click="handleSave"
        >
          {{ plan?.is_saved ? '✅ 已加入' : '☆ 加入我的方案' }}
        </a-button>
      </div>
    </div>

    <!-- 总览 Hero（合并标题+概览） -->
    <div
      v-if="plan"
      class="plan-detail-page__hero"
    >
      <div class="plan-detail-page__hero-main">
        <h1 class="plan-detail-page__hero-title">
          {{ plan.title || (plan as any).trip_name || '行程方案' }}
        </h1>
        <div class="plan-detail-page__hero-meta">
          <span
            v-if="plan.departure || plan.destination"
            class="hero-meta__route"
          >
            {{ plan.departure || (plan as any).origin || '' }}{{ (plan.departure || (plan as any).origin) && (plan.destination || (plan as any).destination) ? ' → ' : '' }}{{ plan.destination || (plan as any).destination || '' }}
          </span>
          <span
            v-if="plan.start_date || plan.end_date"
            class="hero-meta__dates"
          >
            {{ plan.start_date || '' }}{{ plan.start_date && plan.end_date ? ' ~ ' : '' }}{{ plan.end_date || '' }}
          </span>
          <span
            v-if="plan.days"
            class="hero-meta__days"
          >{{ plan.days }}天</span>
          <span
            v-if="plan.people_count"
            class="hero-meta__people"
          >{{ plan.people_count }}人</span>
          <span
            v-if="plan.crowd_type"
            class="hero-meta__crowd"
          >{{ plan.crowd_type }}</span>
        </div>
        <div class="plan-detail-page__hero-stats">
          <div
            v-if="plan.total_budget"
            class="hero-stat"
          >
            <span class="hero-stat__label">总预算</span>
            <span class="hero-stat__value">¥{{ plan.total_budget.toFixed(0) }}</span>
          </div>
          <div
            v-if="plan.estimated_cost"
            class="hero-stat"
          >
            <span class="hero-stat__label">预估花费</span>
            <span class="hero-stat__value">¥{{ plan.estimated_cost.toFixed(0) }}</span>
          </div>
          <div
            v-if="plan.travel_style"
            class="hero-stat"
          >
            <span class="hero-stat__label">风格</span>
            <span class="hero-stat__value">{{ plan.travel_style }}</span>
          </div>
          <div
            v-if="plan.view_count"
            class="hero-stat"
          >
            <span class="hero-stat__label">浏览</span>
            <span class="hero-stat__value">{{ plan.view_count }}</span>
          </div>
        </div>
      </div>
      <div class="plan-detail-page__hero-actions">
        <a-button
          class="hero-action-btn hero-action-btn--primary"
          :loading="isStartingTrip"
          @click="handleStartTrip"
        >
          🚀 {{ isStartingTrip ? '创建中...' : '开始旅行' }}
        </a-button>
        <a-button
          class="hero-action-btn"
          @click="handleFavorite"
        >
          <svg
            :fill="plan.is_favorite ? '#E8A87C' : 'none'"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            stroke="#E8A87C"
            stroke-width="2"
          ><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>
          {{ plan.is_favorite ? '已收藏' : '收藏' }}
        </a-button>
        <a-button
          class="hero-action-btn"
          @click="handleShare"
        >
          🔗 分享
        </a-button>
      </div>
    </div>

    <ShareDialog
      v-model:visible="shareDialogVisible"
      :plan-id="effectivePlanId"
    />

    <!-- 测试数据提示条 -->
    <div
      v-if="useTestData"
      class="test-data-banner"
    >
      <span>🧪 测试数据</span>
    </div>

    <!-- ====== 概览摘要（行程亮点） ====== -->
    <div
      v-if="plan?.overview?.highlights?.length"
      class="plan-detail-page__summary"
    >
      <div class="summary-cards">
        <div
          v-if="plan.overview?.highlights?.length"
          class="summary-card summary-card--highlights"
        >
          <div class="summary-card__header">
            <span class="summary-card__icon">✨</span>
            <span class="summary-card__label">行程亮点</span>
          </div>
          <div class="summary-card__highlight-items">
            <div
              v-for="(h, i) in plan.overview.highlights.slice(0, 4)"
              :key="i"
              class="summary-card__highlight-item"
            >
              <span class="summary-card__highlight-dot" />
              <span class="summary-card__highlight-text">{{ h }}</span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- ====== 每日行程（日程标签 + 卡片，在上方） ====== -->
    <div class="plan-detail-page__daily">
      <PlanTimeline
        v-if="contentBlocks.length"
        :day-count="contentBlocks.filter((b: any) => b.type === 'day_card').length"
        :expanded-days="expandedDays"
        :dates="contentBlocks.filter((b: any) => b.type === 'day_card').map((b: any) => b.data.date)"
        :date-labels="contentBlocks.filter((b: any) => b.type === 'day_card').map((b: any) => b.data.label)"
        @toggle-day="toggleDay"
      />
      <div
        class="plan-detail-page__daily-grid"
        :class="{ 'plan-detail-page__daily-grid--with-budget': budgetOverview }"
      >
        <div class="plan-detail-page__days">
          <div class="plan-detail-page__days-inner">
            <template
              v-for="block in dayCardBlocks"
              :key="block.data.day"
            >
              <DayCard
                v-if="expandedDays.includes(block.data.day)"
                :day="{
                  day: block.data.day,
                  date: block.data.date || '',
                  date_label: block.data.label || '',
                  weather_summary: (block.data as any).weather_summary,
                  day_cost: (block.data as any).day_cost || 0,
                  day_summary: (block.data as any).day_summary || '',
                  activities: (block.data as any).activities || [],
                  accommodation: (block.data as any).accommodation,
                  meals: (block.data as any).meals || [],
                }"
                :expanded="true"
                :markers="dayMarkersMap.get(block.data.day)?.markers || []"
                :route-path="dayMarkersMap.get(block.data.day)?.routePath || []"
                :traffic="((plan as any)?.traffic?.daily_traffic || (plan as any)?.traffic_summary?.daily_traffic || []).find((t: any) => t.day === block.data.day)?.segments || []"
                @toggle="toggleDay"
              />
            </template>
          </div>
        </div>
        <BudgetOverviewCard
          v-if="budgetOverview"
          class="plan-detail-page__budget-overview"
          v-bind="budgetOverview"
        />
      </div>
    </div>

    <!-- ====== 行程详情（详细内容，在下方） ====== -->
    <div class="plan-detail-page__details">
      <BlockRenderer
        v-if="summaryBlocks.length"
        :blocks="summaryBlocks"
      />
      <div
        v-if="!((plan as any)?.content_blocks?.length) && plan"
        class="plan-detail-page__extras"
      >
        <!-- 交通花费表格（在 dailyBlocks 中已作为 text 块插入市内交通指引下方） -->
        <div
          v-if="plan.tips?.length"
          class="plan-detail-page__tips"
        >
          <h3 class="block-section-title">
            💡 出行建议
          </h3>
          <div
            v-for="(tip, i) in plan.tips"
            :key="'t'+i"
            class="block-callout block-callout--info"
          >
            <div class="block-callout__icon">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              ><circle
                cx="12"
                cy="12"
                r="10"
              /><line
                x1="12"
                y1="16"
                x2="12"
                y2="12"
              /><line
                x1="12"
                y1="8"
                x2="12.01"
                y2="8"
              /></svg>
            </div>
            <div class="block-callout__body">
              <div class="block-callout__text">
                {{ tip }}
              </div>
            </div>
          </div>
        </div>
        <div
          v-if="plan.avoid_list?.length"
          class="plan-detail-page__tips"
        >
          <h3 class="block-section-title">
            ⚠️ 避坑提醒
          </h3>
          <div
            v-for="(item, i) in plan.avoid_list"
            :key="'a'+i"
            class="block-callout block-callout--warning"
          >
            <div class="block-callout__icon">
              <svg
                width="20"
                height="20"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              ><path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" /><line
                x1="12"
                y1="9"
                x2="12"
                y2="13"
              /><line
                x1="12"
                y1="17"
                x2="12.01"
                y2="17"
              /></svg>
            </div>
            <div class="block-callout__body">
              <div class="block-callout__text">
                {{ item }}
              </div>
            </div>
          </div>
        </div>
        <WeatherForecast
          v-if="plan.weather_forecast?.length"
          :forecasts="plan.weather_forecast"
        />
        <SouvenirList
          v-if="plan.souvenir_recommendations?.length"
          :items="plan.souvenir_recommendations"
        />
      </div>
    </div>
  </div>

  <LoadingSpinner
    v-else-if="loading"
    size="large"
  />

  <div
    v-else
    class="plan-detail-page__empty"
  >
    <p>方案不存在或加载失败</p>
    <a-button
      type="primary"
      @click="planStore.loadTestPlan(); useTestData = true; loading = false"
    >
      加载测试数据
    </a-button>
  </div>
</template>

<style scoped>
/* ========== 工具栏 ========== */
.plan-detail-page__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-6);
  background: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-border-light);
  gap: var(--space-3);
}
.plan-detail-page__toolbar-right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
.plan-detail-page__back-btn {
  border: none; background: transparent;
  color: var(--color-text-secondary); cursor: pointer;
  font-size: 13px; padding: 4px 0;
}
.plan-detail-page__back-btn:hover { color: var(--color-brand-600); }
.plan-detail-page__save-btn { font-size: 13px; }

/* ========== 总览 Hero ========== */
.plan-detail-page__hero {
  max-width: var(--container-wide);
  margin: 0 auto;
  padding: var(--space-8) var(--space-6) var(--space-4);
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: var(--space-6);
}
.plan-detail-page__hero-title {
  font-size: 26px; font-weight: 700;
  color: var(--color-text-primary); margin: 0 0 var(--space-2);
  line-height: 1.3;
}
.plan-detail-page__hero-meta {
  display: flex; flex-wrap: wrap; gap: var(--space-2);
  font-size: 14px; color: var(--color-text-secondary);
  margin-bottom: var(--space-4);
  line-height: 1.6;
}
.hero-meta__route { font-weight: 500; color: var(--color-brand-600); }
.plan-detail-page__hero-stats {
  display: flex; gap: var(--space-5);
}
.hero-stat { display: flex; flex-direction: column; gap: 2px; }
.hero-stat__label { font-size: 11px; color: var(--color-text-tertiary); }
.hero-stat__value { font-size: 16px; font-weight: 600; color: var(--color-text-primary); }

.plan-detail-page__hero-actions {
  display: flex; gap: var(--space-2); flex-shrink: 0;
}
.hero-action-btn { font-size: 13px !important; }

/* ========== 概览摘要 ========== */
.plan-detail-page__summary {
  max-width: var(--container-wide);
  margin: 0 auto;
  padding: var(--space-4) var(--space-6);
}
.plan-detail-page__extras { margin-top: var(--space-6); }

/* 交通花费汇总 */
.traffic-cost-summary { margin-bottom: var(--space-6); }
.traffic-cost-grid {
  display: flex; flex-wrap: wrap; gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.traffic-cost-item {
  display: flex; flex-direction: column; align-items: center;
  gap: 2px; padding: var(--space-2) var(--space-3);
  background: var(--color-bg-card); border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm); min-width: 64px;
}
.traffic-cost-item--total {
  background: var(--color-brand-50); border-color: var(--color-brand-200);
}
.traffic-cost-item__day { font-size: 11px; font-weight: 600; color: var(--color-text-secondary); }
.traffic-cost-item__time { font-size: 11px; color: var(--color-text-tertiary); }
.traffic-cost-item__cost { font-size: 14px; font-weight: 600; color: var(--color-brand-600); }
.traffic-cost-item--total .traffic-cost-item__cost { font-size: 16px; }
.traffic-cost-note { font-size: 12px; color: var(--color-text-tertiary); padding: var(--space-2); }

/* 概览统计卡片 */
.summary-cards {
  display: flex; gap: var(--space-4);
  margin-bottom: var(--space-6);
}
.summary-card {
  flex: 1; min-width: 0;
  padding: var(--space-5);
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  box-shadow: 0 1px 4px rgba(0,0,0,0.04);
}

.summary-card__header {
  display: flex; align-items: center; gap: var(--space-2);
  margin-bottom: var(--space-3);
}
.summary-card__icon { font-size: 18px; line-height: 1; }
.summary-card__label {
  font-size: 12px; font-weight: 500;
  color: var(--color-text-tertiary);
  text-transform: uppercase; letter-spacing: 0.5px;
}
/* 亮点卡片 */
.summary-card--highlights {
  flex: 2;
  background: linear-gradient(135deg, #F7F9FC 0%, #EEF1F8 100%);
  border: 1px solid #E4E9F2;
}
.summary-card__highlight-items {
  display: flex; flex-direction: column; gap: var(--space-2);
}
.summary-card__highlight-item {
  display: flex; align-items: center; gap: var(--space-2);
}
.summary-card__highlight-dot {
  width: 6px; height: 6px; border-radius: 50%;
  background: var(--color-brand-400);
  flex-shrink: 0;
}
.summary-card__highlight-text {
  font-size: 13px; color: var(--color-text-secondary);
  line-height: 1.4;
}

/* ========== 每日行程（日程标签 + 卡片，在上方） ========== */
.plan-detail-page__daily {
  max-width: var(--container-wide);
  margin: 0 auto;
  padding: 0 var(--space-6) var(--space-6);
}
.plan-detail-page__daily-grid {
  margin-top: var(--space-4);
}
.plan-detail-page__daily-grid--with-budget {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 400px;
  align-items: start;
  gap: var(--space-6);
}
.plan-detail-page__budget-overview {
  position: sticky;
  top: var(--space-4);
}
.plan-detail-page__daily-grid--with-budget .plan-detail-page__days-inner {
  max-width: none;
}

/* ========== 行程详情（详细内容，在下方） ========== */
.plan-detail-page__details {
  max-width: var(--container-wide);
  margin: 0 auto;
  padding: var(--space-6);
  border-top: 1px solid var(--color-border-light);
}
.plan-detail-page__days {
  min-width: 0;
}
.plan-detail-page__days-inner {
  max-width: 800px;
}

@media (max-width: 1080px) {
  .plan-detail-page__daily-grid--with-budget {
    grid-template-columns: 1fr;
  }
  .plan-detail-page__budget-overview {
    position: static;
    order: -1;
  }
}

@media (max-width: 720px) {
  .plan-detail-page__hero { flex-direction: column; }
  .plan-detail-page__hero-actions { flex-wrap: wrap; }
  .plan-detail-page__daily,
  .plan-detail-page__details,
  .plan-detail-page__summary { padding-left: var(--space-3); padding-right: var(--space-3); }
}

/* ========== 通用块样式 ========== */
.block-section-title {
  font-size: 15px; font-weight: 600;
  margin: 24px 0 10px;
  color: var(--color-text-primary);
  display: flex; align-items: center;
}
.block-list-wrapper { margin: 16px 0; }
.block-list { display: flex; flex-wrap: wrap; gap: 6px; }
.block-list__tag {
  display: inline-block; padding: 4px 12px; border-radius: 999px;
  font-size: 12px; background: var(--color-brand-50);
  color: var(--color-brand-700); border: 1px solid var(--color-brand-100);
}
.block-callout {
  display: flex; gap: 12px; padding: 14px 18px;
  border-radius: 10px; margin: 10px 0; border-left: 4px solid;
}
.block-callout--info { background: var(--color-brand-50); border-color: var(--color-brand-300); }
.block-callout--warning { background: var(--color-brand-50); border-color: var(--color-warning); }
.block-callout__icon {
  font-size: 20px; line-height: 1.4; flex-shrink: 0;
  color: var(--color-brand-500); width: 20px; height: 20px;
}
.block-callout--warning .block-callout__icon { color: var(--color-warning); }
.block-callout__body { flex: 1; }
.block-callout__text { font-size: 13px; line-height: 1.5; color: var(--color-text-secondary); }

/* Test data banner */
.test-data-banner {
  background: #EEEDFE; border: 1px solid #CECBF6;
  color: #3C3489; padding: 10px 20px;
  font-size: 13px; text-align: center;
}
</style>
