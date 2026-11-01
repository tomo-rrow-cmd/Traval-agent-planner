// ============================================================
// 方案状态管理
// ============================================================

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type {
  PlanSummary,
  PlanResponse,
  PlanModification,
  PlanExportTask,
  PlanShareResult,
  PlanFavoriteResult,
  TrafficSummary,
  FoodSummary,
  BudgetDetail,
} from '@/types/plan'
import type { SSEDoneData } from '@/types/chat'
import { generatePlanMarkdown } from '@/utils/planMarkdown'
import {
  getPlans as apiGetPlans,
  getPlanDetail as apiGetPlanDetail,
  modifyPlan as apiModifyPlan,
  deletePlan as apiDeletePlan,
  exportPlan as apiExportPlan,
  getExportTaskStatus as apiGetExportTaskStatus,
  downloadExport as apiDownloadExport,
  sharePlan as apiSharePlan,
  toggleFavorite as apiToggleFavorite,
  regeneratePlan as apiRegeneratePlan,
} from '@/api/plan'

const EXPORT_EXTENSIONS_BY_MIME: Record<string, string> = {
  'application/pdf': 'pdf',
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
  'image/png': 'png',
  'text/html': 'html',
  'text/markdown': 'md',
}

export function resolveExportFilename(
  contentDisposition: string | null | undefined,
  contentType: string | null | undefined,
  fallbackBase: string = 'travel_plan',
  fallbackExtension: string = 'pdf',
): string {
  const disposition = contentDisposition || ''
  const encodedMatch = disposition.match(/filename\*\s*=\s*(?:UTF-8'')?([^;]+)/i)
  if (encodedMatch) {
    const encodedName = encodedMatch[1].trim().replace(/^"|"$/g, '')
    try {
      return decodeURIComponent(encodedName)
    } catch {
      return encodedName
    }
  }

  const plainMatch = disposition.match(/filename\s*=\s*"([^"]+)"/i)
    || disposition.match(/filename\s*=\s*([^;\s]+)/i)
  if (plainMatch?.[1]) return plainMatch[1]

  const mime = (contentType || '').split(';', 1)[0].trim().toLowerCase()
  const extension = EXPORT_EXTENSIONS_BY_MIME[mime] || fallbackExtension
  const safeBase = fallbackBase.trim().replace(/[\\/:*?"<>|]/g, '_') || 'travel_plan'
  return `${safeBase}.${extension}`
}

export const usePlanStore = defineStore('plan', () => {
  // ---- state ----

  const plans = ref<PlanSummary[]>([])
  const total = ref(0)
  const currentPlan = ref<PlanResponse | null>(null)
  const isGenerating = ref(false)
  const isModifying = ref(false)
  const generateProgress = ref<{ percent: number; message: string; step?: string } | null>(null)
  const exportTask = ref<PlanExportTask | null>(null)

  /** 轮询导出任务状态（最大 60s、每 2s） */
  async function pollExportTask(
    taskId: string,
    onProgress?: (msg: string) => void,
    expectedFormat: 'pdf' | 'docx' = 'pdf',
  ): Promise<{ blob: Blob; filename: string }> {
    const maxAttempts = 30 // 60s ÷ 2s
    for (let i = 0; i < maxAttempts; i++) {
      const res = await apiGetExportTaskStatus(taskId)
      const data = res.data?.data
      if (!data) break

      if (data.status === 'completed') {
        const dl = await apiDownloadExport(taskId)
        const headers = dl.headers as any
        const disposition = headers?.get?.('content-disposition')
          || headers?.['content-disposition']
          || ''
        const contentType = headers?.get?.('content-type')
          || headers?.['content-type']
          || (dl.data as Blob)?.type
          || ''
        const filename = resolveExportFilename(
          disposition,
          contentType,
          currentPlan.value?.title || 'travel_plan',
          expectedFormat,
        )
        return { blob: dl.data as Blob, filename }
      }
      if (data.status === 'failed') {
        throw new Error(data.error?.message || data.message || '导出失败')
      }
      onProgress?.(data.message || '生成中...')
      await new Promise(r => setTimeout(r, 2000))
    }
    throw new Error('导出超时，请稍后重试')
  }

  /** 图片导出（前端 html2canvas 截图） */
  async function exportImage(
    element: HTMLElement,
    filename: string = 'travel_plan.png',
  ): Promise<void> {
    const html2canvas = (await import('html2canvas')).default
    const canvas = await html2canvas(element, {
      useCORS: true,
      scale: 2,
      backgroundColor: '#ffffff',
      logging: false,
    })
    const blob = await new Promise<Blob | null>(resolve =>
      canvas.toBlob(resolve, 'image/png'),
    )
    if (!blob) throw new Error('截图生成失败')
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  /** PDF 导出（纯前端 html2canvas + jsPDF） */
  async function exportPdf(
    element: HTMLElement,
    filename: string = 'travel_plan.pdf',
  ): Promise<void> {
    const html2canvas = (await import('html2canvas')).default
    const { jsPDF } = await import('jspdf')
    const canvas = await html2canvas(element, {
      useCORS: true,
      scale: 2,
      backgroundColor: '#ffffff',
      logging: false,
    })
    const pdf = new jsPDF('p', 'mm', 'a4')
    const margin = 10
    const pageWidth = pdf.internal.pageSize.getWidth() - margin * 2
    const pageHeight = pdf.internal.pageSize.getHeight() - margin * 2
    const pagePixelHeight = Math.floor(canvas.width * pageHeight / pageWidth)

    for (let sourceY = 0, page = 0; sourceY < canvas.height; sourceY += pagePixelHeight, page++) {
      if (page > 0) pdf.addPage()
      const sliceHeight = Math.min(pagePixelHeight, canvas.height - sourceY)
      const pageCanvas = document.createElement('canvas')
      pageCanvas.width = canvas.width
      pageCanvas.height = sliceHeight
      const context = pageCanvas.getContext('2d')
      if (!context) throw new Error('PDF 页面生成失败')
      context.drawImage(
        canvas,
        0,
        sourceY,
        canvas.width,
        sliceHeight,
        0,
        0,
        canvas.width,
        sliceHeight,
      )
      const renderedHeight = sliceHeight * pageWidth / canvas.width
      pdf.addImage(
        pageCanvas.toDataURL('image/png'),
        'PNG',
        margin,
        margin,
        pageWidth,
        renderedHeight,
        undefined,
        'FAST',
      )
    }
    pdf.save(filename)
  }

  /** DOCX 导出（使用当前 Markdown 生成器保持字段兼容） */
  async function exportDocx(filename: string = 'travel_plan.docx'): Promise<void> {
    const { Document, HeadingLevel, Packer, Paragraph } = await import('docx')
    if (!currentPlan.value) throw new Error('无方案数据')
    const markdown = generatePlanMarkdown(currentPlan.value as any)
    const paragraphs = markdown.split('\n').map((line) => {
      const text = line.trim()
      if (text.startsWith('### ')) {
        return new Paragraph({ text: text.slice(4), heading: HeadingLevel.HEADING_3 })
      }
      if (text.startsWith('## ')) {
        return new Paragraph({ text: text.slice(3), heading: HeadingLevel.HEADING_2 })
      }
      if (text.startsWith('# ')) {
        return new Paragraph({ text: text.slice(2), heading: HeadingLevel.HEADING_1 })
      }
      return new Paragraph({ text: text.replace(/^[-*] /, '') })
    })
    const docxDocument = new Document({ sections: [{ children: paragraphs }] })
    const blob = await Packer.toBlob(docxDocument)
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = filename.replace(/\.docx$/, '') + '.docx'
    document.body.appendChild(anchor)
    anchor.click()
    document.body.removeChild(anchor)
    URL.revokeObjectURL(url)
  }

  /** 按会话隔离的 localStorage 缓存键 */
  function getPlanCacheKey(sessionId?: string): string {
    return sessionId ? `cached_plan_${sessionId}` : 'cached_plan'
  }

  /** 初始化时尝试从 localStorage 恢复缓存的方案 */
  function restoreCachedPlan(sessionId?: string): PlanResponse | null {
    try {
      const key = getPlanCacheKey(sessionId)
      const raw = localStorage.getItem(key)
      if (raw) {
        const parsed = JSON.parse(raw) as PlanResponse
        if ((!parsed.id || parsed.id === 'detail') && parsed.days && parsed.daily_itinerary?.length) {
          parsed.id = `local_${Date.now()}`
          parsed._id = parsed.id
          localStorage.setItem(key, JSON.stringify(parsed))
        }
        currentPlan.value = parsed
        return parsed
      }
    } catch { /* ignore corrupt cache */ }
    return null
  }

  /** 将当前方案按会话持久化到 localStorage */
  function persistCurrentPlan(sessionId?: string): void {
    if (currentPlan.value) {
      localStorage.setItem(getPlanCacheKey(sessionId), JSON.stringify(currentPlan.value))
    }
  }

  /** 清除指定会话的持久化缓存 */
  function clearPlanCache(sessionId?: string): void {
    if (sessionId) {
      localStorage.removeItem(getPlanCacheKey(sessionId))
    } else {
      localStorage.removeItem(getPlanCacheKey())
    }
  }

  // 初始化时不自动恢复缓存（由 ChatSessionPage 加载指定会话的缓存）
  // restoreCachedPlan() 改为由外部按 sessionId 调用

  // ---- actions ----

  /**
   * 获取方案列表
   */
  async function fetchPlans(page: number = 1, page_size: number = 20): Promise<void> {
    const result = await apiGetPlans({ page, page_size })
    plans.value = result.data?.data?.list ?? []
    total.value = result.data?.data?.total ?? 0
  }

  /**
   * 获取方案详情
   */
  async function fetchPlanDetail(planId: string, sessionId?: string): Promise<void> {
    const result = await apiGetPlanDetail(planId)
    currentPlan.value = result.data?.data ?? null
    persistCurrentPlan(sessionId)
  }

  /**
   * 更新生成进度
   */
  function updateProgress(data: { percent: number; message: string; step?: string }): void {
    generateProgress.value = data
  }

  /**
   * 修改方案
   */
  async function modifyPlan(
    planId: string,
    modifications: PlanModification[],
  ): Promise<void> {
    isModifying.value = true
    try {
      await apiModifyPlan(planId, { modifications })
      // 重新获取最新方案详情
      await fetchPlanDetail(planId)
    } finally {
      isModifying.value = false
    }
  }

  /**
   * 删除方案
   */
  async function deletePlan(planId: string): Promise<void> {
    await apiDeletePlan(planId)
    plans.value = plans.value.filter((p) => p.id !== planId)
    if (currentPlan.value?.id === planId) {
      clearCurrentPlan()
    }
  }

  /**
   * 重新生成方案（SSE 流式响应）
   */
  async function regeneratePlan(planId: string, sessionId: string): Promise<void> {
    isGenerating.value = true
    generateProgress.value = { percent: 0, message: '开始重新生成方案...' }
    try {
      await apiRegeneratePlan(planId, { session_id: sessionId })
      await fetchPlanDetail(planId)
    } finally {
      isGenerating.value = false
      generateProgress.value = null
    }
  }

  /**
   * 导出方案
   */
  async function exportPlan(
    planId: string,
    format: 'md' | 'pdf' | 'image' | 'docx',
  ): Promise<PlanExportTask> {
    const result = await apiExportPlan(planId, format)
    exportTask.value = result.data!.data!
    return result.data!.data!
  }

  /**
   * 分享方案
   */
  async function sharePlan(
    planId: string,
    options?: { expire_in?: number; password?: string },
  ): Promise<PlanShareResult> {
    const result = await apiSharePlan(planId, options)
    return result.data!.data!
  }

  /**
   * 切换收藏状态
   */
  async function toggleFavorite(planId: string): Promise<PlanFavoriteResult> {
    const result = await apiToggleFavorite(planId)
    const favorited = result.data!.data!
    // 更新列表中对应的收藏状态
    const target = plans.value.find((p) => p.id === planId)
    if (target) {
      target.is_favorite = favorited.is_favorite
    }
    if (currentPlan.value?.id === planId) {
      currentPlan.value.is_favorite = favorited.is_favorite
    }
    return favorited
  }

  /**
   * 清空当前方案（清除内存状态）
   */
  function clearCurrentPlan(sessionId?: string): void {
    currentPlan.value = null
    isGenerating.value = false
    isModifying.value = false
    generateProgress.value = null
    exportTask.value = null
    // 同时清理对应会话的 localStorage 缓存，避免跨会话污染
    clearPlanCache(sessionId)
  }

  /**
   * 将 SSE done 事件的 summary 转换为 Partial<PlanResponse>
   * 用于在生成完成后快速填充 UI 预览
   */
  function mapSSESummaryToPlan(summary: SSEDoneData['summary'] | null): Partial<PlanResponse> | null {
    if (!summary) return null
    return {
      destination: summary.destination,
      days: summary.days,
      daily_itinerary: summary.daily_plan as PlanResponse['daily_itinerary'],
      food_summary: (summary.meal_plan ?? []) as unknown as FoodSummary,
      traffic_summary: (summary.traffic ?? {}) as unknown as TrafficSummary,
      budget_detail: (summary.budget ?? {}) as unknown as BudgetDetail,
      souvenir_recommendations: summary.souvenirs as PlanResponse['souvenir_recommendations'],
    } as Partial<PlanResponse>
  }

  /**
   * 将 SSE summary 标准化为 PlanResponse 兼容格式
   * SSE summary 的字段名和结构跟 PlanResponse 不一致，需要转换
   */
  function normalizeSSESummary(summary: Record<string, any>): Partial<PlanResponse> {
    // 调试日志
     
    console.log('[normalizeSSESummary] input keys:', Object.keys(summary), 'daily_itinerary length:', summary.daily_itinerary?.length)
     
    console.log('[normalizeSSESummary] meal_plan:', Array.isArray(summary.meal_plan) ? summary.meal_plan.length + 'items' : typeof summary.meal_plan,
      'weather_forecast:', Array.isArray(summary.weather_forecast) ? summary.weather_forecast.length + 'items' : typeof summary.weather_forecast,
      'hotel_plan keys:', summary.hotel_plan ? Object.keys(summary.hotel_plan) : 'no hotel_plan',
      'day0 meals:', summary.daily_itinerary?.[0]?.meals?.length + 'items, keys=' + Object.keys(summary.daily_itinerary?.[0] || {}).join(','))

    // 转换 daily_itinerary: attractions[] → activities[]
    const rawItinerary: any[] = summary.daily_itinerary || summary.daily_plan || []
    const daily_itinerary = rawItinerary.map((day: any, idx: number) => {
      const rawActs = day.attractions || day.activities || []
       
      console.log(`[normalizeSSESummary] day ${day.day}: rawActs count=${rawActs.length}, keys=${Object.keys(day)}`)
      return {
        day: day.day ?? (idx + 1),
        date: day.date || '',
        date_label: day.date_label || '',
        weather_summary: day.weather_summary || '',
        day_cost: day.day_cost || 0,
        day_summary: day.day_summary || '',
        activities: rawActs.map((a: any) => ({
          time_slot: a.time_slot || '',
          type: a.type || 'attraction',
          title: a.name || a.title || '',
          subtitle: a.subtitle || '',
          description: a.reason || a.description || '',
          duration_minutes: a.duration_hours ? Math.round(a.duration_hours * 60) : undefined,
          cost: a.price || a.cost || 0,
          rating: a.rating || 0,
          tags: a.tags || [],
          tips: a.tips || '',
          location: a.latitude && a.longitude ? { lat: a.latitude, lng: a.longitude } : undefined,
        })),
        accommodation: day.hotel || day.accommodation || undefined,
        // 从单独的 meal_plan 查找餐饮数据
        meals: (() => {
          if (day.meals?.length) return day.meals
          const mp = (summary.meal_plan || []).find((m: any) => m.day === day.day)
          return mp?.meals || []
        })(),
        traffic: day.traffic || [],
      }
    })

    return {
      id: summary.id || '',
      title: summary.trip_name || `${summary.destination || ''}之旅`,
      destination: summary.destination || '',
      departure: summary.origin || '',
      days: summary.days || 0,
      start_date: summary.start_date || '',
      end_date: summary.end_date || '',
      total_budget: summary.budget?.total_budget || 0,
      estimated_cost: summary.budget?.actual_total || 0,
      // ----- 以下字段对齐 PlanResponse 命名，供 PlanDetailPage 使用 -----
      daily_itinerary: daily_itinerary as any,
      traffic_summary: {
        city_to_city: [] as any[],
        city_internal: '',
        daily_traffic: summary.traffic?.daily_traffic || [],
        daily_plan: summary.traffic?.daily_plan || [],
        summary: summary.traffic?.summary || '',
        total_traffic_cost: summary.traffic?.total_traffic_cost || 0,
      } as TrafficSummary,
      food_summary: {
        recommended_restaurants: [] as any[],
        total_food_budget: 0,
        meal_plan: summary.meal_plan || [],
        recommendations: summary.meal_plan || [],
      } as FoodSummary,
      budget_detail: (() => {
        const details = summary.budget?.details || []
        const totalBudget = summary.budget?.total_budget || 0
        // 辅助：按分类名查找（兼容中英文）
        function findCat(...names: string[]): number {
          for (const name of names) {
            const d = details.find((x: any) => x.category === name)
            if (d) return d.spent ?? d.budget ?? 0
          }
          return 0
        }
        const catMap: Record<string, { label: string; names: string[] }> = {
          transport: { label: '交通', names: ['交通', 'transport', 'traffic'] },
          accommodation: { label: '住宿', names: ['住宿', 'accommodation', 'hotel'] },
          food: { label: '美食', names: ['餐饮', 'food', 'meal'] },
          attractions: { label: '景点', names: ['门票', 'attractions', 'ticket'] },
          souvenirs: { label: '纪念品', names: ['购物', 'souvenirs', 'shopping'] },
          contingency: { label: '备用', names: ['备用', 'contingency', 'other'] },
        }
        const breakdown: Record<string, any> = {}
        for (const [key, cfg] of Object.entries(catMap)) {
          const spent = findCat(...cfg.names)
          breakdown[key] = {
            amount: spent,
            percent: totalBudget > 0 ? Math.round((spent / totalBudget) * 100) : 0,
            items: [],
          }
        }
        return { total: totalBudget, breakdown } as BudgetDetail
      })(),
      souvenir_recommendations: summary.souvenirs || [],
      weather_forecast: (summary.weather_forecast || []).map((f: any) => ({
        date: f.date || f.fxDate || '',
        weather: f.weather || f.dayweather || '',
        temp_high: f.temp_high ?? f.tempMax ?? f.daytemp ?? null,
        temp_low: f.temp_low ?? f.tempMin ?? f.nighttemp ?? null,
        wind: f.wind || (f.daywind ? f.daywind + (f.daypower ? ' ' + f.daypower + '级' : '') : '') || '',
        humidity: f.humidity ?? null,
        precipitation: f.precipitation ?? null,
        aqi: f.aqi ?? null,
        advice: f.advice || f.text || '',
      })),
      packing_list: summary.packing_list || [],
      tips: summary.tips || [],
      avoid_list: summary.avoid_list || [],
      // ----- 前端面板直接读取的原始配置 -----
      trip_config: summary.trip_config || {},
      pace: summary.trip_config?.pace || summary.pace || '',
      // ----- 以下字段对齐 PlanPreview 旧有读取（保留兼容） -----
      traffic: {
        daily_traffic: summary.traffic?.daily_traffic || [],
        summary: summary.traffic?.summary || '',
        total_traffic_cost: summary.traffic?.total_traffic_cost || 0,
      },
      big_traffic: summary.big_traffic || [],
      hotel_plan: summary.hotel_plan || {},
      meal_plan: summary.meal_plan || summary.mealPlan || [],
      budget: summary.budget || {},
      // ----- 通用字段 -----
      people_count: summary.travelers || 1,
      version: 1,
      is_favorite: false,
      view_count: summary.view_count || 0,
      crowd_type: summary.crowd_type || summary.trip_config?.crowd_type || '',
      // 从 final_plan 的 traffic 数据中提取概览信息
      overview: (() => {
        const highlights = (
          summary.highlights ||
          summary.overview?.highlights ||
          []
        )
        // 从交通数据中提取总里程和交通方式
        const dailyTraffic = summary.traffic?.daily_traffic || []
        let totalDistanceKm = summary.overview?.total_distance_km ?? 0
        const transportModes = new Set<string>()
        for (const dt of dailyTraffic) {
          for (const seg of dt.segments || []) {
            if (typeof seg.distance_km === 'number') totalDistanceKm += seg.distance_km
            if (seg.mode) transportModes.add(seg.mode)
          }
        }
        // 也尝试从 big_traffic 提取城际交通方式
        const bigTraffic = summary.big_traffic || {}
        if (bigTraffic.recommend_mode) transportModes.add(bigTraffic.recommend_mode)
        return {
          highlights: highlights as string[],
          total_distance_km: totalDistanceKm,
          transport_modes: Array.from(transportModes),
        }
      })(),
    }
  }

  function loadTestPlan(): void {
    currentPlan.value = {
      id: 'test_plan_001',
      title: '长沙7日深度游',
      destination: '长沙',
      departure: '广州',
      start_date: '2026-07-10',
      end_date: '2026-07-16',
      days: 7,
      people_count: 2,
      crowd_type: '朋友/情侣',
      total_budget: 5000,
      estimated_cost: 4652,
      travel_style: '深度游',
      status: 'completed',
      version: 1,
      is_favorite: true,
      view_count: 128,
      // ---- 方案概览 ----
      overview: {
        highlights: [
          '湖南省博物馆马王堆汉墓惊世文物',
          '登岳麓山俯瞰湘江橘子洲全景',
          '太平老街坡子街地道美食之旅',
          '梅溪湖国际文化艺术中心建筑打卡',
          '湘江夜游感受星城魅力',
        ],
        total_distance_km: 42,
        transport_modes: ['地铁', '步行', '打车', '公交'],
      },
      // ---- 每日行程 ----
      daily_itinerary: [
        {
          day: 1, date: '2026-07-10', date_label: '周五',
          weather_summary: '晴 32°C',
          day_cost: 315,
          day_summary: '从千年学府到湘江中心，感受长沙的历史底蕴与自然风光。',
          activities: [
            { time_slot: '09:00-12:00', type: 'attraction', title: '岳麓山', subtitle: '南大门上东大门下经典路线', description: '长沙地标，海拔300米。先参观岳麓书院(四大书院之一)，登顶俯瞰湘江和橘子洲全景。顺路看爱晚亭"停车坐爱枫林晚"。建议穿舒适步行鞋。', cost: 0, duration_minutes: 180, rating: 4.7, tags: ['文化', '必去', '自然'], tips: '建议南大门上东大门下，可避开人流', location: { lng: 112.947, lat: 28.193 } },
            { time_slot: '14:00-17:00', type: 'attraction', title: '橘子洲', subtitle: '毛泽东青年时期常游之地', description: '湘江中心狭长岛屿，长5公里。核心是毛泽东青年艺术雕塑(高32米)。可乘小火车(¥20)往返，傍晚夕阳洒江面是最佳拍照时间。', cost: 0, duration_minutes: 120, rating: 4.5, tags: ['经典', '拍照', '红色'], tips: '傍晚前往光线最佳，小火车末班17:30', location: { lng: 112.960, lat: 28.175 } },
            { time_slot: '18:00-21:00', type: 'food', title: '太平老街', subtitle: '长沙最有烟火气的老街', description: '保存最完好的历史街区，汇集黑色经典臭豆腐、糖油粑粑、长沙大香肠等标志性小吃。建议晚上前往，灯光下更有韵味。', cost: 60, duration_minutes: 120, rating: 4.6, tags: ['美食', '夜景', '老街'], tips: '臭豆腐推荐黑色经典，糖油粑粑推荐李公庙', location: { lng: 112.978, lat: 28.197 } },
          ],
          accommodation: { hotel_name: '匠宿酒店(五一广场)', address: '芙蓉区五一广场', room_type: '标准间', price: 400, rating: 4.7, check_in: '14:00', check_out: '12:00', location: { lng: 112.979, lat: 28.195 } },
        },
        {
          day: 2, date: '2026-07-11', date_label: '周六',
          weather_summary: '多云 30°C',
          day_cost: 432,
          day_summary: '深入文化内核，从千年古墓到古城墙的历史回望。',
          activities: [
            { time_slot: '09:00-12:00', type: 'attraction', title: '湖南省博物馆', subtitle: '国家级博物馆·马王堆汉墓', description: '国家一级博物馆。最大看点马王堆汉墓——辛追夫人遗体(2100年不腐)、素纱襌衣(49克)、T型帛画。免费但需公众号预约，周一闭馆。', cost: 0, duration_minutes: 180, rating: 4.9, tags: ['文化', '博物馆', '必去'], tips: '提前3天公众号预约，周末建议9点前到', location: { lng: 113.004, lat: 28.209 } },
            { time_slot: '13:00-15:00', type: 'attraction', title: '天心阁', subtitle: '长沙古城标志', description: '长沙古城标志，明代始建。登顶俯瞰古城风貌，附近保留明清城墙遗迹。', cost: 32, duration_minutes: 90, rating: 4.2, tags: ['历史', '登高'], location: { lng: 112.982, lat: 28.186 } },
            { time_slot: '17:00-20:00', type: 'food', title: '坡子街', subtitle: '火宫殿所在地', description: '最负盛名美食街。火宫殿(260年历史)聚集长沙最全小吃。推荐：口味虾、臭豆腐、剁椒鱼头。', cost: 120, duration_minutes: 150, rating: 4.5, tags: ['美食', '夜市'], tips: '火宫殿人均¥60-80，建议多点小份', location: { lng: 112.976, lat: 28.191 } },
          ],
          accommodation: { hotel_name: '匠宿酒店(五一广场)', address: '芙蓉区五一广场', room_type: '标准间', price: 400, rating: 4.7, check_in: null, check_out: null, location: { lng: 112.979, lat: 28.195 } },
        },
        {
          day: 3, date: '2026-07-12', date_label: '周日',
          weather_summary: '阵雨 28°C',
          day_cost: 280,
          day_summary: '自然与艺术碰撞，从城市绿肺到世界级建筑地标。',
          activities: [
            { time_slot: '09:00-11:30', type: 'attraction', title: '湖南省植物园', subtitle: '城市森林氧吧', description: '140公顷城市森林氧吧。世界名花园、樱花园等园区，夏季绿树成荫适合散步拍照。', cost: 20, duration_minutes: 150, rating: 4.3, tags: ['自然', '拍照'], tips: '夏季蚊虫多建议带驱蚊水', location: { lng: 113.028, lat: 28.118 } },
            { time_slot: '14:00-16:00', type: 'attraction', title: '梅溪湖文化艺术中心', subtitle: '扎哈·哈迪德遗作', description: '扎哈·哈迪德遗作，三朵芙蓉花造型流线型建筑。即使不看演出，外围散步拍照也很值。', cost: 0, duration_minutes: 90, rating: 4.6, tags: ['建筑', '打卡', '艺术'], location: { lng: 112.897, lat: 28.193 } },
            { time_slot: '17:00-19:00', type: 'shopping', title: '万家丽国际MALL', subtitle: '亚洲最大单体建筑之一', description: '亚洲最大单体建筑之一。顶层空中花园(28F)俯瞰城市天际线，傍晚看日落绝佳。', cost: 80, duration_minutes: 120, rating: 4.1, tags: ['逛街', '日落'], tips: '顶层日落约18:30-19:00', location: { lng: 113.035, lat: 28.195 } },
          ],
          accommodation: { hotel_name: '匠宿酒店(五一广场)', address: '芙蓉区五一广场', room_type: '标准间', price: 400, rating: 4.7, location: { lng: 112.979, lat: 28.195 } },
        },
        {
          day: 4, date: '2026-07-13', date_label: '周一',
          weather_summary: '多云 31°C',
          day_cost: 356,
          day_summary: '文艺打卡日，从历史街区到现代书店再到湘江夜景。',
          activities: [
            { time_slot: '10:00-12:00', type: 'attraction', title: '潮宗街历史文化街区', subtitle: '长沙版"宽窄巷子"', description: '新晋网红打卡地。清末民初建筑群，文创小店、咖啡馆林立。比太平街更清净文艺。', cost: 0, duration_minutes: 120, rating: 4.4, tags: ['文艺', '拍照', '网红'], location: { lng: 112.973, lat: 28.200 } },
            { time_slot: '14:00-16:00', type: 'rest', title: '止间书店', subtitle: '长沙最美书店', description: '大学城附近的人文书店，空间设计极具格调。适合午后阅读发呆，有独立咖啡区。', cost: 35, duration_minutes: 120, rating: 4.5, tags: ['文艺', '书店', '咖啡'], location: { lng: 112.946, lat: 28.184 } },
            { time_slot: '18:30-21:00', type: 'entertainment', title: '湘江夜游', subtitle: '乘游船赏星城夜景', description: '乘游船沿湘江航行，欣赏两岸灯光秀。杜甫江阁→橘子洲大桥→渔人码头段最美。', cost: 100, duration_minutes: 120, rating: 4.6, tags: ['夜景', '游船', '浪漫'], tips: '提前美团购票¥80，选19:30班次', location: { lng: 112.970, lat: 28.179 } },
          ],
          accommodation: { hotel_name: '匠宿酒店(五一广场)', room_type: '标准间', price: 400, rating: 4.7, location: { lng: 112.979, lat: 28.195 } },
        },
        {
          day: 5, date: '2026-07-14', date_label: '周二',
          weather_summary: '晴 33°C',
          day_cost: 512,
          day_summary: '美食探索日，从早市到夜市沉浸式体验长沙味道。',
          activities: [
            { time_slot: '07:00-09:00', type: 'food', title: '南门口早市', subtitle: '老长沙早餐圣地', description: '长沙最接地气的早市。推荐：公交新村粉店(牛肉粉¥16)、糖油佗佗、葱油粑粑。', cost: 30, duration_minutes: 120, rating: 4.5, tags: ['美食', '早市', '地道'], location: { lng: 112.982, lat: 28.186 } },
            { time_slot: '10:00-12:00', type: 'attraction', title: '贾谊故居', subtitle: '西汉著名政论家故居', description: '西汉著名政论家贾谊故居，位于太平街。免费参观，了解长沙两千年历史变迁。', cost: 0, duration_minutes: 60, rating: 4.0, tags: ['历史', '文化'], location: { lng: 112.977, lat: 28.196 } },
            { time_slot: '12:30-14:00', type: 'food', title: '费大厨辣椒炒肉', subtitle: '长沙必吃榜第一名', description: '长沙最火爆的湘菜馆。招牌辣椒炒肉¥68，皮蛋青椒擂茄子¥32，人均¥70。', cost: 140, duration_minutes: 90, rating: 4.7, tags: ['美食', '湘菜', '必吃'], tips: '11点前去取号，否则排队2小时+', location: { lng: 112.981, lat: 28.193 } },
            { time_slot: '18:00-21:00', type: 'food', title: '渔人码头美食街', subtitle: '湘江边的大排档一条街', description: '湘江西岸集中了20+家品质湘菜馆。推荐：老街鱼嘴巴、文和友龙虾馆。江边座位风景绝佳。', cost: 180, duration_minutes: 180, rating: 4.4, tags: ['美食', '江景', '夜市'], tips: '提前订江边座位', location: { lng: 112.958, lat: 28.223 } },
          ],
          accommodation: { hotel_name: '匠宿酒店(五一广场)', price: 400, rating: 4.7, location: { lng: 112.979, lat: 28.195 } },
        },
        {
          day: 6, date: '2026-07-15', date_label: '周三',
          weather_summary: '晴 34°C',
          day_cost: 420,
          day_summary: '主题乐园日，在欢乐中释放多巴胺。',
          activities: [
            { time_slot: '09:30-17:00', type: 'entertainment', title: '长沙方特东方神画', subtitle: '高科技主题乐园', description: '大型文化主题乐园，以中国传统文化为核心。推荐项目：女娲补天(4D过山车)、牛郎织女(空中旋转)、九州神韵(巨幕影院)。', cost: 280, duration_minutes: 420, rating: 4.5, tags: ['乐园', '刺激', '文化'], tips: '下载方特APP查看排队时长，带防晒', location: { lng: 112.812, lat: 28.117 } },
            { time_slot: '18:30-20:00', type: 'food', title: '四方坪夜市', subtitle: '本地人最爱夜市', description: '长沙本地人最爱的夜市之一。李记飞饼、烤猪蹄、里脊肉串、芝士烤榴莲，人均¥50吃到撑。', cost: 100, duration_minutes: 90, rating: 4.6, tags: ['美食', '夜市', '本地'], location: { lng: 113.012, lat: 28.224 } },
          ],
          accommodation: { hotel_name: '长沙梅溪湖金茂豪华精选酒店', price: 650, rating: 4.8, location: { lng: 112.898, lat: 28.194 } },
        },
        {
          day: 7, date: '2026-07-16', date_label: '周四',
          weather_summary: '多云 30°C',
          day_cost: 287,
          day_summary: '最后一天轻松收尾，带些纪念品返程。',
          activities: [
            { time_slot: '09:00-11:00', type: 'shopping', title: '黄兴路步行街', subtitle: '长沙最繁华商业街', description: '长沙最繁华的商业步行街。品牌旗舰店+特色小吃+文创集市。可以采购伴手礼。', cost: 200, duration_minutes: 120, rating: 4.2, tags: ['购物', '步行街'], location: { lng: 112.979, lat: 28.192 } },
            { time_slot: '12:00-13:30', type: 'food', title: '一盏灯长沙菜', subtitle: '地道湘菜馆', description: '本地人力荐的湘菜馆。招牌：酸萝卜炒肚丝、鸭掌筋、口味鸡杂。人均¥65。', cost: 130, duration_minutes: 90, rating: 4.6, tags: ['美食', '湘菜'], tips: '不能吃辣记得说微辣', location: { lng: 112.980, lat: 28.190 } },
            { time_slot: '14:30-16:00', type: 'transport', title: '长沙南站返程', subtitle: '高铁返回广州', description: '长沙南站→广州南站，高铁约2.5-3小时。建议提前1小时到站。', cost: 628, duration_minutes: 180, rating: 0, tags: ['交通', '返程'], location: { lng: 113.059, lat: 28.145 } },
          ],
        },
      ],
      // ---- 交通 ----
      traffic_summary: {
        city_to_city: [
          { mode: '高铁', from: '广州南', to: '长沙南', price: 314, duration: '2h30m', recommendation: '推荐G6102次，08:30-11:00快车' },
        ],
        city_internal: '长沙地铁已覆盖主要景点。6条线路，下载长沙地铁APP或微信/支付宝乘车码。3日票¥40不限次。打车起步价¥8，市内主要景点间¥15-30。',
      },
      // ---- 市内交通（每日分段路线，给 DayCard 交通明细使用） ----
      traffic: {
        daily_traffic: [
          { day: 1, total_time_min: 68, total_cost: 16, segments: [
            { from: '匠宿酒店(五一广场)', to: '岳麓山', mode: '地铁', distance_km: 5.2, time_min: 25, cost: 4 },
            { from: '岳麓山', to: '橘子洲', mode: '地铁', distance_km: 3.8, time_min: 18, cost: 4 },
            { from: '橘子洲', to: '太平老街', mode: '步行', distance_km: 1.5, time_min: 20, cost: 0 },
            { from: '太平老街', to: '匠宿酒店(五一广场)', mode: '步行', distance_km: 0.5, time_min: 5, cost: 0 },
          ] },
          { day: 2, total_time_min: 52, total_cost: 22, segments: [
            { from: '匠宿酒店(五一广场)', to: '湖南省博物馆', mode: '打车', distance_km: 4.5, time_min: 15, cost: 14 },
            { from: '湖南省博物馆', to: '天心阁', mode: '打车', distance_km: 3.2, time_min: 12, cost: 8 },
            { from: '天心阁', to: '坡子街', mode: '步行', distance_km: 0.8, time_min: 10, cost: 0 },
            { from: '坡子街', to: '匠宿酒店(五一广场)', mode: '步行', distance_km: 1.0, time_min: 15, cost: 0 },
          ] },
          { day: 3, total_time_min: 88, total_cost: 24, segments: [
            { from: '匠宿酒店(五一广场)', to: '湖南省植物园', mode: '公交', distance_km: 8.5, time_min: 40, cost: 4 },
            { from: '湖南省植物园', to: '梅溪湖文化艺术中心', mode: '公交', distance_km: 7.2, time_min: 30, cost: 4 },
            { from: '梅溪湖文化艺术中心', to: '万家丽国际MALL', mode: '打车', distance_km: 6.0, time_min: 18, cost: 16 },
            { from: '万家丽国际MALL', to: '匠宿酒店(五一广场)', mode: '步行', distance_km: 0, time_min: 0, cost: 0 },
          ] },
          { day: 4, total_time_min: 85, total_cost: 18, segments: [
            { from: '匠宿酒店(五一广场)', to: '潮宗街', mode: '步行', distance_km: 1.2, time_min: 15, cost: 0 },
            { from: '潮宗街', to: '止间书店', mode: '步行', distance_km: 0.8, time_min: 10, cost: 0 },
            { from: '止间书店', to: '湘江夜游码头', mode: '打车', distance_km: 3.5, time_min: 15, cost: 12 },
            { from: '湘江夜游码头', to: '匠宿酒店(五一广场)', mode: '步行', distance_km: 2.0, time_min: 25, cost: 0 },
          ] },
          { day: 5, total_time_min: 90, total_cost: 16, segments: [
            { from: '匠宿酒店(五一广场)', to: '南门口早市', mode: '步行', distance_km: 1.0, time_min: 12, cost: 0 },
            { from: '南门口早市', to: '费大厨辣椒炒肉', mode: '步行', distance_km: 0.5, time_min: 8, cost: 0 },
            { from: '费大厨辣椒炒肉', to: '渔人码头美食街', mode: '打车', distance_km: 5.0, time_min: 20, cost: 16 },
            { from: '渔人码头美食街', to: '匠宿酒店(五一广场)', mode: '打车', distance_km: 4.5, time_min: 18, cost: 14 },
          ] },
          { day: 6, total_time_min: 75, total_cost: 50, segments: [
            { from: '匠宿酒店(五一广场)', to: '方特东方神画', mode: '打车', distance_km: 20.0, time_min: 35, cost: 40 },
            { from: '方特东方神画', to: '四方坪夜市', mode: '打车', distance_km: 8.0, time_min: 20, cost: 10 },
            { from: '四方坪夜市', to: '梅溪湖金茂豪华精选酒店', mode: '打车', distance_km: 6.0, time_min: 20, cost: 18 },
          ] },
          { day: 7, total_time_min: 25, total_cost: 8, segments: [
            { from: '匠宿酒店(五一广场)', to: '黄兴路步行街', mode: '步行', distance_km: 0.8, time_min: 10, cost: 0 },
            { from: '黄兴路步行街', to: '一盏灯长沙菜', mode: '步行', distance_km: 0.3, time_min: 5, cost: 0 },
            { from: '一盏灯长沙菜', to: '长沙南站', mode: '地铁', distance_km: 8.0, time_min: 30, cost: 6 },
          ] },
        ],
        summary: '长沙市内交通以地铁为主，市区景点密集处步行即可。远郊方特建议打车。每日交通费约¥16-50。',
        total_traffic_cost: 154,
      },
      // ---- 美食 ----
      food_summary: {
        recommended_restaurants: [
          { name: '费大厨辣椒炒肉', cuisine: '湘菜', avg_price: 70, rating: 4.7, recommended_dishes: ['辣椒炒肉', '皮蛋青椒擂茄子', '香煎鲫鱼'] },
          { name: '一盏灯长沙菜', cuisine: '湘菜', avg_price: 65, rating: 4.6, recommended_dishes: ['酸萝卜炒肚丝', '鸭掌筋', '口味鸡杂'] },
          { name: '火宫殿', cuisine: '湘菜小吃', avg_price: 60, rating: 4.4, recommended_dishes: ['臭豆腐', '糖油粑粑', '姊妹团子'] },
        ],
        total_food_budget: 910,
      },
      // ---- 预算（BudgetChart 兼容格式） ----
      budget_detail: {
        total: 5000,
        breakdown: {
          transport: { amount: 942, percent: 19, items: [{ name: '广州-长沙高铁', cost: 628 }, { name: '市内交通', cost: 314 }] },
          accommodation: { amount: 2650, percent: 53, items: [{ name: '匠宿酒店5晚', cost: 2000 }, { name: '梅溪湖酒店1晚', cost: 650 }] },
          food: { amount: 910, percent: 18, items: [{ name: '日常餐饮', cost: 760 }, { name: '夜市小吃', cost: 150 }] },
          attractions: { amount: 432, percent: 9, items: [{ name: '方特门票', cost: 280 }, { name: '湘江游船', cost: 100 }, { name: '其他门票', cost: 52 }] },
          souvenirs: { amount: 200, percent: 4, items: [{ name: '伴手礼', cost: 200 }] },
          contingency: { amount: 500, percent: 10, items: [] },
        },
      },
      // ---- 纪念品 ----
      souvenir_recommendations: [
        { name: '黑色经典臭豆腐礼盒', description: '长沙特产，真空包装方便携带', estimated_price: '¥68/盒', buy_place: '太平老街·黑色经典旗舰店' },
        { name: '湘绣手帕', description: '中国四大名绣之一，手工刺绣精美', estimated_price: '¥88-388', buy_place: '湖南省博物馆文创店' },
        { name: '文和友小龙虾酱料', description: '地道长沙风味，回家也能做出口味虾', estimated_price: '¥35/瓶', buy_place: '海信广场·文和友旗舰店' },
        { name: '岳麓书院文创书签', description: '岳麓书院主题金属书签，精致典雅', estimated_price: '¥28', buy_place: '岳麓书院出口文创店' },
      ],
      // ---- 天气预报 ----
      weather_forecast: [
        { date: '2026-07-10', weather: '晴', temp_high: 32, temp_low: 26, wind: '南风2级', humidity: 65, precipitation: 0, aqi: 52, advice: '注意防晒，建议携带遮阳伞' },
        { date: '2026-07-11', weather: '多云', temp_high: 30, temp_low: 25, wind: '南风1级', humidity: 70, precipitation: 0, aqi: 48, advice: '户外活动适宜' },
        { date: '2026-07-12', weather: '阵雨', temp_high: 28, temp_low: 23, wind: '北风2级', humidity: 80, precipitation: 8, advice: '建议携带雨伞，植物园可能泥泞' },
        { date: '2026-07-13', weather: '多云', temp_high: 31, temp_low: 25, wind: '南风2级', humidity: 68, precipitation: 0, aqi: 55, advice: '适合江边活动' },
        { date: '2026-07-14', weather: '晴', temp_high: 33, temp_low: 26, wind: '南风3级', humidity: 60, precipitation: 0, aqi: 60, advice: '高温日，注意防暑' },
        { date: '2026-07-15', weather: '晴', temp_high: 34, temp_low: 27, wind: '南风2级', humidity: 58, precipitation: 0, aqi: 65, advice: '方特游玩务必防晒补水' },
        { date: '2026-07-16', weather: '多云', temp_high: 30, temp_low: 24, wind: '北风1级', humidity: 72, precipitation: 0, aqi: 50, advice: '返程日天气良好' },
      ],
      // ---- 行李清单 ----
      packing_list: [
        '身份证', '手机+充电器+充电宝', '防晒霜SPF50+', '遮阳帽', '便携风扇',
        '肠胃药(湘菜偏辣)', '雨伞/遮阳伞', '舒适的步行鞋', '换洗衣物3-4套',
        '洗漱用品', '少量现金', '学生证(部分景点半价)',
      ],
      // ---- 出行建议 ----
      tips: [
        '长沙夏季炎热(30-35°C)，建议防晒伞+防晒霜+便携风扇三件套必备',
        '湘菜普遍偏辣，肠胃不好的建议备好肠胃药，点菜时说"微辣"',
        '每天步行1-2万步，务必穿舒适的鞋子',
        '湖南省博物馆周一闭馆，需提前3天在公众号预约',
        '地铁已覆盖大部分景点，微信/支付宝可直接扫码乘车',
        '岳麓山建议南大门上东大门下，可避开大部分旅行团',
      ],
      // ---- 避坑清单 ----
      avoid_list: [
        '不要相信出租车司机推荐的"便宜一日游"，基本都是购物团',
        '太平街、坡子街的水果捞价格较高（¥30+），不推荐购买',
        '景区门口兜售的"祈福带""同心锁"价格虚高，不建议购买',
        '火宫殿的小吃价格偏贵，味道不如旁边的小巷子',
        '雨季(6-7月)湘江游船可能因水位停航，提前电话确认',
        '方特附近的"黑车"要价高，建议直接打车或坐公交',
      ],
      created_at: '2026-07-09T10:00:00Z',
      updated_at: '2026-07-09T14:30:00Z',
      // ====== 新增字段（PlanDetail 扩展） ======
      meal_plan: [
        { day: 1, meals: [{ meal: '午餐', restaurant: '费大厨辣椒炒肉', avg_price: 70, reason: '长沙必吃榜第一名' }, { meal: '晚餐', restaurant: '太平老街小吃', avg_price: 40, reason: '品尝各类长沙小吃' }] },
        { day: 2, meals: [{ meal: '午餐', restaurant: '一盏灯长沙菜', avg_price: 65, reason: '本地人力荐湘菜馆' }, { meal: '晚餐', restaurant: '火宫殿', avg_price: 60, reason: '百年老字号小吃王国' }] },
        { day: 3, meals: [{ meal: '午餐', restaurant: '公交新村粉店', avg_price: 16, reason: '长沙最火米粉店' }, { meal: '晚餐', restaurant: '渔人码头美食街', avg_price: 80, reason: '湘江边吃海鲜大排档' }] },
        { day: 4, meals: [{ meal: '午餐', restaurant: '鲁哥饭店', avg_price: 55, reason: '地道长沙家常菜' }, { meal: '晚餐', restaurant: '盟重烧烤', avg_price: 70, reason: '网红烧烤店' }] },
        { day: 5, meals: [{ meal: '午餐', restaurant: '南门口早市', avg_price: 25, reason: '老长沙早餐圣地' }, { meal: '晚餐', restaurant: '文和友龙虾馆', avg_price: 100, reason: '长沙必打卡的龙虾馆' }] },
        { day: 6, meals: [{ meal: '午餐', restaurant: '四方坪夜市', avg_price: 50, reason: '本地人最爱夜市' }, { meal: '晚餐', restaurant: '茶颜悦色+小吃', avg_price: 35, reason: '长沙特色奶茶' }] },
        { day: 7, meals: [{ meal: '午餐', restaurant: '一盏灯长沙菜', avg_price: 65, reason: '最后一餐回味湘菜' }, { meal: '晚餐', restaurant: '长沙南站快餐', avg_price: 40, reason: '返程前简单解决' }] },
      ],
      hotel_plan: {
        recommendations: [
          { name: '匠宿酒店(五一广场)', price_per_night: 400, rating: 4.7, address: '芙蓉区五一广场', reason: '市中心核心位置，步行可达太平街', commute_score: 0.92, latitude: 28.195, longitude: 112.979 },
          { name: '长沙梅溪湖金茂豪华精选酒店', price_per_night: 650, rating: 4.8, address: '梅溪湖路', reason: '湖景房，毗邻文化艺术中心', commute_score: 0.78, latitude: 28.194, longitude: 112.898 },
        ],
        selected: '匠宿酒店(五一广场)',
        selected_hotel: { name: '匠宿酒店(五一广场)', price_per_night: 400, rating: 4.7, address: '芙蓉区五一广场', latitude: 28.195, longitude: 112.979 },
        selection_reason: '交通评分 0.92 最优，距离核心景点近',
      },
      big_traffic: [{
        trains: [
          { trainCode: 'G6102', fromStationName: '广州南', toStationName: '长沙南', departureTime: '08:30', arrivalTime: '11:00', duration: '2h30m', prices: { '二等座': 314, '一等座': 504, '商务座': 998 } },
          { trainCode: 'G6112', fromStationName: '广州南', toStationName: '长沙南', departureTime: '09:15', arrivalTime: '12:45', duration: '3h30m', prices: { '二等座': 314, '一等座': 504 } },
          { trainCode: 'G6028', fromStationName: '广州南', toStationName: '长沙南', departureTime: '14:30', arrivalTime: '17:55', duration: '3h25m', prices: { '二等座': 299, '一等座': 478 } },
        ],
        return_trains: [
          { trainCode: 'G6033', fromStationName: '长沙南', toStationName: '广州南', departureTime: '15:30', arrivalTime: '18:20', duration: '2h50m', prices: { '二等座': 314, '一等座': 504 } },
          { trainCode: 'G6125', fromStationName: '长沙南', toStationName: '广州南', departureTime: '18:00', arrivalTime: '21:10', duration: '3h10m', prices: { '二等座': 299, '一等座': 478 } },
        ],
        recommend_mode: 'train',
        city_distance_km: 707,
      }],
      budget: {
        total_budget: 5000,
        actual_total: 4652,
        remaining: 348,
        details: [
          { category: '交通', budget: 942, spent: 942, remaining: 0, status: 'ok' },
          { category: '住宿', budget: 2650, spent: 2650, remaining: 0, status: 'ok' },
          { category: '餐饮', budget: 910, spent: 560, remaining: 350, status: 'ok' },
          { category: '门票', budget: 432, spent: 200, remaining: 232, status: 'ok' },
          { category: '购物', budget: 200, spent: 300, remaining: -100, status: 'over' },
        ],
        warnings: ['购物超预算 ¥100'],
        suggestions: [{ action: '减少购物支出', save: 100 }],
        per_person_per_day: Math.round(4652 / 7),
      },
    } as any
    isGenerating.value = false
    persistCurrentPlan()
  }

  /**
   * 加载测试方案：成都美食5日行
   */
  function loadTestPlanChengdu(): void {
    currentPlan.value = {
      id: 'test_chengdu',
      title: '成都美食5日行',
      destination: '成都',
      departure: '广州',
      start_date: '2026-08-15',
      end_date: '2026-08-19',
      days: 5,
      people_count: 2,
      crowd_type: '朋友/情侣',
      total_budget: 5000,
      estimated_cost: 4230,
      travel_style: '美食之旅',
      status: 'completed',
      version: 1,
      is_favorite: false,
      view_count: 86,
      pace: '适中',
      overview: {
        highlights: [
          '宽窄巷子+锦里双古街美食扫街',
          '大熊猫繁育基地近距离看熊猫',
          '都江堰水利工程古人的智慧',
          '九眼桥夜景+成都夜生活体验',
          '川菜博物馆体验正宗宫保鸡丁',
        ],
        total_distance_km: 55,
        transport_modes: ['地铁', '打车', '景区直通车'],
      },
      daily_itinerary: [
        {
          day: 1, date: '2026-08-15', date_label: '周六',
          weather_summary: '多云 31°C',
          day_cost: 380,
          day_summary: '抵达成都，从宽窄巷子到锦里，感受成都的慢生活与美食。',
          activities: [
            { time_slot: '14:00-17:00', type: 'attraction', title: '宽窄巷子', subtitle: '清代古街·成都名片', description: '由宽巷子、窄巷子、井巷子组成，青砖黛瓦的清末建筑群。最成都的市井生活缩影，喝茶掏耳朵看变脸。', cost: 0, duration_minutes: 180, rating: 4.5, tags: ['文化', '美食', '必去'], tips: '下午去光线好，晚上灯笼亮起更美', location: { lng: 104.058, lat: 30.670 } },
            { time_slot: '18:00-21:00', type: 'food', title: '锦里', subtitle: '三国文化美食街', description: '紧邻武侯祠的仿古美食街，红灯笼夜景绝美。三大炮、钵钵鸡、肥肠粉、张飞牛肉，人均¥60-80吃到撑。', cost: 80, duration_minutes: 150, rating: 4.6, tags: ['美食', '夜景', '老街'], tips: '晚上比白天更有氛围，推荐三大炮和糖油果子', location: { lng: 104.051, lat: 30.646 } },
          ],
          meals: [
            { meal: '晚餐', restaurant: '皇城老妈火锅', avg_price: 120, cuisine: '川味火锅', reason: '成都老字号火锅，牛油锅底浓郁，推荐毛肚和黄喉' },
            { meal: '小吃', restaurant: '锦里美食街', avg_price: 60, cuisine: '成都小吃', reason: '三大炮、钵钵鸡、糖油果子一次尝遍' },
          ],
          accommodation: { hotel_name: '成都太古里亚朵S酒店', address: '锦江区东大街', room_type: '几木大床房', price: 450, rating: 4.8, check_in: '14:00', check_out: '12:00', location: { lng: 104.084, lat: 30.653 } },
        },
        {
          day: 2, date: '2026-08-16', date_label: '周日',
          weather_summary: '晴 33°C',
          day_cost: 420,
          day_summary: '熊猫基地看国宝，下午逛太古里感受时尚成都，晚上吃地道串串。',
          activities: [
            { time_slot: '08:00-12:00', type: 'attraction', title: '大熊猫繁育研究基地', subtitle: '全球最大熊猫保护基地', description: '距市区10公里，占地1000亩。看熊猫的最佳时间是早上，熊猫活跃度高。月亮产房看幼年熊猫，太阳产房看刚出生的熊猫宝宝。', cost: 58, duration_minutes: 240, rating: 4.8, tags: ['自然', '亲子', '必去'], tips: '建议7:30前到门口排队，熊猫8-10点最活跃', location: { lng: 104.144, lat: 30.733 } },
            { time_slot: '14:00-17:00', type: 'shopping', title: '成都远洋太古里', subtitle: '开放式街区购物中心', description: '结合川西建筑风格的开放式商业街区。大慈寺就在旁边，现代与传统完美融合。品牌旗舰店+独立设计师店+网红餐厅。', cost: 100, duration_minutes: 180, rating: 4.5, tags: ['购物', '网红', '建筑'], location: { lng: 104.082, lat: 30.653 } },
            { time_slot: '19:00-21:00', type: 'food', title: '建设巷小吃街', subtitle: '成都本地人最爱的夜市', description: '成都电子科大旁边的夜市，价格亲民味道正宗。推荐：烤脑花、炸串串、锅巴土豆、醪糟汤圆。人均¥40吃到扶墙。', cost: 60, duration_minutes: 120, rating: 4.7, tags: ['美食', '夜市', '本地'], tips: '下午6点后出摊，早点去不排队', location: { lng: 104.081, lat: 30.669 } },
          ],
          meals: [
            { meal: '午餐', restaurant: '马旺子·川小馆', avg_price: 85, cuisine: '新派川菜', reason: '太古里人气川菜，推荐水煮鱼和宫保虾球' },
            { meal: '晚餐', restaurant: '山城风串串王', avg_price: 55, cuisine: '串串', reason: '建设巷老店，牛油锅底正宗，牛肉串¥0.6/串' },
          ],
          accommodation: { hotel_name: '成都太古里亚朵S酒店', price: 450, rating: 4.8, location: { lng: 104.084, lat: 30.653 } },
        },
        {
          day: 3, date: '2026-08-17', date_label: '周一',
          weather_summary: '多云 30°C',
          day_cost: 380,
          day_summary: '都江堰一日游，感受千年水利工程的智慧，晚上体验川剧变脸。',
          activities: [
            { time_slot: '09:00-16:00', type: 'attraction', title: '都江堰景区', subtitle: '世界文化遗产·千年水利工程', description: '距成都55公里，战国李冰父子主持修建。鱼嘴分水堤、飞沙堰溢洪道、宝瓶口引水口三大工程至今运转。景区+离堆公园+二王庙。', cost: 90, duration_minutes: 360, rating: 4.7, tags: ['文化', '历史', '世界遗产'], tips: '建议请导游讲解，不然看不懂工程原理', location: { lng: 103.607, lat: 31.002 } },
            { time_slot: '18:30-20:30', type: 'entertainment', title: '蜀风雅韵川剧变脸', subtitle: '地道川剧表演', description: '琴台路文化公园内的川剧剧场。变脸、喷火、滚灯、手影戏，近距离感受非遗文化。VIP席含盖碗茶和小吃。', cost: 120, duration_minutes: 120, rating: 4.6, tags: ['文化', '表演', '非遗'], tips: '提前一天订票，前排体验更好', location: { lng: 104.049, lat: 30.659 } },
          ],
          meals: [
            { meal: '午餐', restaurant: '都江堰农家菜', avg_price: 50, cuisine: '川菜', reason: '景区附近农家乐，推荐青城山老腊肉' },
            { meal: '晚餐', restaurant: '小龙坎老火锅', avg_price: 100, cuisine: '川味火锅', reason: '成都最火爆的连锁火锅，推荐鹅肠和毛肚' },
          ],
          accommodation: { hotel_name: '成都太古里亚朵S酒店', price: 450, rating: 4.8 },
        },
        {
          day: 4, date: '2026-08-18', date_label: '周二',
          weather_summary: '晴 32°C',
          day_cost: 350,
          day_summary: '武侯祠+杜甫草堂感受人文成都，下午体验川菜博物馆DIY宫保鸡丁。',
          activities: [
            { time_slot: '09:00-11:30', type: 'attraction', title: '武侯祠', subtitle: '三国文化圣地', description: '中国唯一君臣合祀祠庙，纪念诸葛亮、刘备及蜀汉英雄。红墙夹道是网红拍照点。', cost: 60, duration_minutes: 150, rating: 4.5, tags: ['历史', '文化', '三国'], location: { lng: 104.050, lat: 30.646 } },
            { time_slot: '13:00-15:00', type: 'attraction', title: '杜甫草堂', subtitle: '诗圣故居', description: '杜甫流寓成都时的故居，茅屋为秋风所破歌创作地。园林式博物馆，红墙绿竹幽静雅致。', cost: 50, duration_minutes: 120, rating: 4.4, tags: ['文化', '诗词', '园林'], tips: '春季花开最美，夏季绿树成荫', location: { lng: 104.031, lat: 30.663 } },
            { time_slot: '16:00-18:00', type: 'food', title: '川菜博物馆', subtitle: '可以吃的博物馆', description: '位于郫都区，现场展示川菜历史+制作工艺。亲手DIY宫保鸡丁+熊猫蒸饺，做完当场吃掉。', cost: 98, duration_minutes: 120, rating: 4.5, tags: ['美食', '体验', '文化'], tips: 'DIY需提前预约，约1.5小时', location: { lng: 103.938, lat: 30.794 } },
          ],
          meals: [
            { meal: '午餐', restaurant: '陈麻婆豆腐(总店)', avg_price: 65, cuisine: '川菜', reason: '百年老店，麻婆豆腐¥28一份，最正宗的川菜味道' },
            { meal: '晚餐', restaurant: '饕林餐厅', avg_price: 80, cuisine: '自贡菜', reason: '太古里人气川菜，推荐鲜椒兔和火爆黄喉' },
          ],
          accommodation: { hotel_name: '成都太古里亚朵S酒店', price: 450, rating: 4.8 },
        },
        {
          day: 5, date: '2026-08-19', date_label: '周三',
          weather_summary: '多云 29°C',
          day_cost: 280,
          day_summary: '最后一天轻松收尾，人民公园喝盖碗茶体验成都慢生活，采购特产返程。',
          activities: [
            { time_slot: '09:00-11:30', type: 'attraction', title: '人民公园', subtitle: '成都慢生活代表', description: '成都最接地气的公园。鹤鸣茶社喝盖碗茶(¥20)，看本地人打麻将掏耳朵。保路运动纪念碑也在园内。', cost: 20, duration_minutes: 150, rating: 4.5, tags: ['休闲', '文化', '本地'], tips: '鹤鸣茶社上午人少，找个湖边位置', location: { lng: 104.058, lat: 30.660 } },
            { time_slot: '13:00-15:00', type: 'shopping', title: '春熙路', subtitle: '成都最繁华商圈', description: '成都百年商业街，IFS爬墙熊猫打卡点。采购伴手礼：火锅底料、张飞牛肉、川酒、蜀绣。', cost: 150, duration_minutes: 120, rating: 4.3, tags: ['购物', '商圈'], location: { lng: 104.083, lat: 30.656 } },
            { time_slot: '16:00-17:30', type: 'transport', title: '成都东站返程', subtitle: '高铁返回广州', description: '成都东站→广州南站，高铁约7-8小时。建议提前1小时到站，成都东站很大预留时间。', cost: 634, duration_minutes: 150, rating: 0, tags: ['交通', '返程'] },
          ],
          meals: [
            { meal: '午餐', restaurant: '鸡毛店·川菜馆', avg_price: 60, cuisine: '川菜', reason: '春熙路附近，价格实惠味道好，推荐蒜泥白肉' },
          ],
        },
      ],
      traffic_summary: {
        city_to_city: [
          { mode: '高铁', from: '广州南', to: '成都东', price: 634, duration: '7h30m', recommendation: '推荐G1312次，08:30-16:00直达' },
        ],
        city_internal: '成都地铁已覆盖主要景点。12条线路，下载成都地铁APP或支付宝扫码。打车起步价¥8，市区景点间¥10-30。',
      },
      traffic: {
        daily_traffic: [
          { day: 1, total_time_min: 60, total_cost: 28, segments: [
            { from: '成都东站', to: '太古里', mode: '地铁', distance_km: 8, time_min: 25, cost: 5 },
            { from: '太古里', to: '宽窄巷子', mode: '步行', distance_km: 1.5, time_min: 15, cost: 0 },
            { from: '宽窄巷子', to: '锦里', mode: '打车', distance_km: 2, time_min: 10, cost: 12 },
            { from: '锦里', to: '太古里', mode: '打车', distance_km: 3, time_min: 10, cost: 11 },
          ] },
          { day: 2, total_time_min: 80, total_cost: 36, segments: [
            { from: '太古里', to: '熊猫基地', mode: '景区直通车', distance_km: 12, time_min: 35, cost: 10 },
            { from: '熊猫基地', to: '太古里', mode: '打车', distance_km: 12, time_min: 25, cost: 26 },
          ] },
          { day: 3, total_time_min: 110, total_cost: 60, segments: [
            { from: '太古里', to: '都江堰', mode: '打车', distance_km: 55, time_min: 50, cost: 50 },
            { from: '都江堰', to: '琴台路', mode: '打车', distance_km: 55, time_min: 60, cost: 60 },
          ] },
          { day: 5, total_time_min: 55, total_cost: 16, segments: [
            { from: '太古里', to: '人民公园', mode: '步行', distance_km: 1, time_min: 10, cost: 0 },
            { from: '人民公园', to: '春熙路', mode: '步行', distance_km: 1.5, time_min: 15, cost: 0 },
            { from: '春熙路', to: '成都东站', mode: '地铁', distance_km: 8, time_min: 30, cost: 6 },
          ] },
        ],
        summary: '成都地铁方便，市区景点密集处步行即可。远郊都江堰建议打车或景区直通车。',
        total_traffic_cost: 140,
      },
      budget: { total_budget: 5000, actual_total: 4230, details: [
        { category: '交通', budget: 1400, spent: 1342, remaining: 58, status: 'ok' },
        { category: '住宿', budget: 1800, spent: 1800, remaining: 0, status: 'ok' },
        { category: '餐饮', budget: 1000, spent: 740, remaining: 260, status: 'ok' },
        { category: '门票', budget: 500, spent: 378, remaining: 122, status: 'ok' },
        { category: '购物', budget: 300, spent: 250, remaining: 50, status: 'ok' },
      ], per_person_per_day: 423, suggestions: [
        { action: '餐饮预算有结余，可以多尝试小吃', save: 0 },
      ]},
      budget_detail: { total: 5000, breakdown: {
        transport: { amount: 1342, percent: 27, items: [{ name: '广州-成都高铁', cost: 634 }, { name: '市内交通', cost: 140 }] },
        accommodation: { amount: 1800, percent: 36, items: [{ name: '亚朵S酒店4晚', cost: 1800 }] },
        food: { amount: 740, percent: 15, items: [{ name: '日常餐饮', cost: 560 }, { name: '夜市小吃', cost: 180 }] },
        attractions: { amount: 378, percent: 8, items: [{ name: '都江堰', cost: 90 }, { name: '熊猫基地', cost: 58 }, { name: '其他门票', cost: 230 }] },
        souvenirs: { amount: 250, percent: 5, items: [{ name: '特产手信', cost: 250 }] },
        contingency: { amount: 500, percent: 10, items: [] },
      }},
      weather_forecast: [
        { date: '2026-08-15', weather: '多云', temp_high: 31, temp_low: 23, wind: '南风2级', humidity: 72, advice: '适宜出行，建议携带薄外套' },
        { date: '2026-08-16', weather: '晴', temp_high: 33, temp_low: 24, wind: '南风1级', humidity: 65, advice: '熊猫基地注意防晒' },
        { date: '2026-08-17', weather: '多云', temp_high: 30, temp_low: 22, wind: '北风2级', humidity: 68, advice: '都江堰比市区凉快，建议带外套' },
        { date: '2026-08-18', weather: '晴', temp_high: 32, temp_low: 23, wind: '南风2级', humidity: 60, advice: '适合户外活动' },
        { date: '2026-08-19', weather: '多云', temp_high: 29, temp_low: 22, wind: '北风1级', humidity: 70, advice: '返程日天气良好' },
      ],
      hotel_plan: { recommendations: [
        { name: '成都太古里亚朵S酒店', price_per_night: 450, rating: 4.8, address: '锦江区东大街', reason: '太古里核心位置，地铁2号线直达，周边餐饮丰富' },
        { name: '成都群光君悦酒店', price_per_night: 880, rating: 4.7, address: '春熙路商圈', reason: '五星级酒店，高空大堂俯瞰成都夜景' },
      ], selected: '成都太古里亚朵S酒店' },
      meal_plan: [
        { day: 1, meals: [{ meal: '晚餐', restaurant: '皇城老妈火锅', avg_price: 120 }] },
        { day: 2, meals: [{ meal: '午餐', restaurant: '马旺子·川小馆', avg_price: 85 }] },
        { day: 3, meals: [{ meal: '午餐', restaurant: '都江堰农家菜', avg_price: 50 }] },
        { day: 4, meals: [{ meal: '午餐', restaurant: '陈麻婆豆腐', avg_price: 65 }] },
        { day: 5, meals: [{ meal: '午餐', restaurant: '鸡毛店·川菜馆', avg_price: 60 }] },
      ],
      attraction_details: [
        { name: '宽窄巷子', tips: ['下午去光线好适合拍照', '晚上灯笼亮起更有氛围'], famous_spots: ['宽巷子-拴马石', '窄巷子-小洋楼'], address: '成都市青羊区长顺街' },
        { name: '大熊猫繁育研究基地', tips: ['建议7:30前到门口排队', '熊猫8-10点最活跃'], famous_spots: ['月亮产房', '太阳产房'], address: '成都市成华区熊猫大道' },
        { name: '都江堰', tips: ['建议请导游讲解', '穿舒适步行鞋'], famous_spots: ['鱼嘴分水堤', '二王庙'], address: '成都市都江堰市公园路' },
      ],
      food_details: [
        { name: '皇城老妈火锅', signature_dishes: ['老妈牛肉', '鲜毛肚', '黄喉'] },
        { name: '马旺子·川小馆', signature_dishes: ['水煮鱼', '宫保虾球', '鸡豆花'] },
      ],
      packing_list: ['身份证', '手机+充电宝', '防晒霜', '薄外套', '舒适的步行鞋', '肠胃药(川菜偏辣)', '雨伞'],
      tips: ['成都地铁已覆盖主要景点，下载成都地铁APP', '火锅必点毛肚黄喉，微辣适合外地人', '春熙路IFS爬墙熊猫是打卡热点'],
      avoid_list: ['不要相信景区门口的"低价一日游"', '宽窄巷子里的水果捞价格偏高', '锦里小吃价格比外面贵，尝尝即可'],
      souvenirs: ['火锅底料', '张飞牛肉', '郫县豆瓣酱', '蜀绣手帕'],
      souvenir_recommendations: [
        { name: '火锅底料', description: '成都火锅的灵魂，真空包装方便携带', estimated_price: '¥25-50/袋', buy_place: '春熙路·王府井超市' },
        { name: '张飞牛肉', description: '成都特产，五香/麻辣多种口味', estimated_price: '¥68/袋', buy_place: '宽窄巷子·特产店' },
      ],
      per_person_per_day: 423,
    } as any
    isGenerating.value = false
    persistCurrentPlan()
  }

  /**
   * 加载测试方案：北京3日文化之旅
   */
  function loadTestPlanBeijing(): void {
    currentPlan.value = {
      id: 'test_beijing',
      title: '北京3日文化之旅',
      destination: '北京',
      departure: '上海',
      start_date: '2026-08-05',
      end_date: '2026-08-07',
      days: 3,
      people_count: 1,
      crowd_type: '独自旅行',
      total_budget: 3000,
      estimated_cost: 2650,
      travel_style: '文化深度',
      status: 'completed',
      version: 1,
      is_favorite: false,
      view_count: 42,
      pace: '紧凑',
      overview: {
        highlights: ['故宫博物院感受六百年皇城', '八达岭长城做好汉', '天安门广场看升旗仪式', '什刹海胡同文化体验'],
        total_distance_km: 120,
        transport_modes: ['地铁', '公交', '步行'],
      },
      daily_itinerary: [
        {
          day: 1, date: '2026-08-05', date_label: '周三',
          weather_summary: '晴 35°C',
          day_cost: 380,
          day_summary: '天安门广场+故宫+景山公园，中轴线经典一日游。',
          activities: [
            { time_slot: '06:30-07:00', type: 'attraction', title: '天安门广场升旗', subtitle: '庄严的升旗仪式', description: '每天日出时分国旗护卫队护送国旗升起，建议提前1小时到。', cost: 0, duration_minutes: 30, rating: 4.7, tags: ['必去', '红色'], tips: '提前查升旗时间，建议6点前到' },
            { time_slot: '08:30-14:00', type: 'attraction', title: '故宫博物院', subtitle: '世界五大宫之首', description: '明清两代皇家宫殿，600年历史。中轴三大殿+西六宫+珍宝馆。', cost: 60, duration_minutes: 300, rating: 4.9, tags: ['文化', '历史', '必去'], tips: '提前7天公众号预约，走中轴线2.5h' },
            { time_slot: '15:00-16:30', type: 'attraction', title: '景山公园', subtitle: '俯瞰故宫全景最佳位置', description: '故宫北门对面，万春亭俯瞰故宫中轴线全景。崇祯皇帝自缢处。', cost: 2, duration_minutes: 90, rating: 4.6, tags: ['拍照', '登高'], tips: '傍晚光线最佳，门票¥2超值' },
          ],
          meals: [
            { meal: '午餐', restaurant: '故宫冰窖餐厅', avg_price: 60, cuisine: '简餐', reason: '故宫内的特色餐厅，由清代冰窖改造' },
            { meal: '晚餐', restaurant: '四季民福烤鸭(故宫店)', avg_price: 120, cuisine: '北京菜', reason: '景观位看故宫角楼，烤鸭外酥里嫩' },
          ],
          accommodation: { hotel_name: '北京王府井漫心酒店', address: '东城区王府井', room_type: '大床房', price: 400, rating: 4.5, check_in: '14:00', check_out: '12:00' },
        },
        {
          day: 2, date: '2026-08-06', date_label: '周四',
          weather_summary: '多云 33°C',
          day_cost: 500,
          day_summary: '八达岭长城一日游，晚上逛什刹海胡同。',
          activities: [
            { time_slot: '07:00-14:00', type: 'attraction', title: '八达岭长城', subtitle: '世界文化遗产', description: '明长城最精华段，海拔1015米。可步行登城或坐缆车(¥140往返)。好汉坡必打卡。', cost: 45, duration_minutes: 360, rating: 4.8, tags: ['历史', '户外', '必去'], tips: '早去避开人流，北段比南段壮观' },
            { time_slot: '17:00-20:00', type: 'attraction', title: '什刹海', subtitle: '老北京胡同文化', description: '前海+后海+西海组成。恭王府、醇亲王府等众多王府云集。烟袋斜街逛胡同小店。', cost: 0, duration_minutes: 180, rating: 4.5, tags: ['文化', '胡同', '夜景'] },
          ],
          meals: [
            { meal: '午餐', restaurant: '长城景区快餐', avg_price: 40, cuisine: '简餐', reason: '景区内简餐，建议自带干粮' },
            { meal: '晚餐', restaurant: '南门涮肉(什刹海店)', avg_price: 100, cuisine: '老北京涮肉', reason: '铜锅涮肉，手切鲜羊肉是招牌' },
          ],
          accommodation: { hotel_name: '北京王府井漫心酒店', price: 400, rating: 4.5 },
        },
        {
          day: 3, date: '2026-08-07', date_label: '周五',
          weather_summary: '多云 32°C', day_cost: 350,
          day_summary: '天坛+颐和园，皇家园林与祭祀文化。',
          activities: [
            { time_slot: '08:00-10:30', type: 'attraction', title: '天坛公园', subtitle: '明清帝王祭天之所', description: '中国现存最大的古代祭祀建筑群。祈年殿是北京地标，回音壁有神奇声学效果。', cost: 35, duration_minutes: 150, rating: 4.7, tags: ['文化', '历史', '建筑'] },
            { time_slot: '13:00-17:00', type: 'attraction', title: '颐和园', subtitle: '皇家园林博物馆', description: '中国古典园林之最。万寿山+昆明湖+长廊(世界最长画廊)。佛香阁俯瞰全景。', cost: 30, duration_minutes: 240, rating: 4.7, tags: ['园林', '历史', '拍照'] },
          ],
          meals: [
            { meal: '午餐', restaurant: '大董烤鸭(王府井店)', avg_price: 150, cuisine: '北京菜', reason: '高端烤鸭代表，酥不腻烤鸭是招牌' },
          ],
        },
      ],
      traffic: { daily_traffic: [
        { day: 1, total_time_min: 70, total_cost: 18, segments: [{ from: '王府井', to: '天安门', mode: '步行', time_min: 10, cost: 0 }, { from: '天安门', to: '故宫', mode: '步行', time_min: 5, cost: 0 }, { from: '故宫', to: '景山', mode: '步行', time_min: 10, cost: 0 }] },
        { day: 2, total_time_min: 180, total_cost: 30, segments: [{ from: '王府井', to: '北京北站', mode: '地铁', time_min: 30, cost: 5 }, { from: '北京北站', to: '八达岭', mode: 'S2线', time_min: 90, cost: 8 }] },
      ], summary: '北京地铁覆盖广，推荐办交通卡或刷NFC。S2线去八达岭性价比高。' },
      budget: { total_budget: 3000, actual_total: 2650, details: [
        { category: '交通', budget: 600, spent: 550, status: 'ok' },
        { category: '住宿', budget: 800, spent: 800, status: 'ok' },
        { category: '餐饮', budget: 700, spent: 530, status: 'ok' },
        { category: '门票', budget: 400, spent: 232, status: 'ok' },
        { category: '购物', budget: 500, spent: 538, status: 'over' },
      ], per_person_per_day: 883 },
      weather_forecast: [
        { date: '2026-08-05', weather: '晴', temp_high: 35, temp_low: 26, advice: '高温日注意防暑' },
        { date: '2026-08-06', weather: '多云', temp_high: 33, temp_low: 25, advice: '长城注意防晒' },
        { date: '2026-08-07', weather: '多云', temp_high: 32, temp_low: 24, advice: '适宜出行' },
      ],
      packing_list: ['身份证', '学生证', '防晒霜', '遮阳帽', '舒适的步行鞋', '充电宝', '水杯'],
      tips: ['故宫提前7天预约', '八达岭S2线可用交通卡', '北京地铁支持NFC'],
      avoid_list: ['不要在前门大街买高价特产', '八达岭缆车排队人多，可以步行'],
      per_person_per_day: 883,
    } as any
    isGenerating.value = false
    persistCurrentPlan()
  }

  function loadTestPlanQingdao(): void {
    currentPlan.value = {
      id: 'test_qingdao', title: '青岛3日海滨之旅', destination: '青岛', departure: '北京',
      start_date: '2026-07-20', end_date: '2026-07-22', days: 3, people_count: 2,
      crowd_type: '朋友/情侣', total_budget: 5000, estimated_cost: 4230,
      travel_style: '海滨休闲', status: 'completed', version: 1, is_favorite: false,
      view_count: 56, pace: '适中',
      trip_config: { pace: '适中', travelers: 2, preferences: ['海滨', '美食'] },
      overview: { highlights: ['栈桥-五四广场-奥帆中心经典海岸线','崂山太清宫-仰口一线山海奇观','八大关万国建筑群文艺漫步','青岛啤酒博物馆原浆畅饮','船歌鱼水饺·本地人推荐的鲅鱼水饺'], total_distance_km: 38, transport_modes: ['地铁','打车','步行','公交'] },
      daily_itinerary: [
        { day:1, date:'2026-07-20', date_label:'周一', weather_summary:'晴 28°C', day_cost:420, day_summary:'抵达青岛，漫步百年栈桥，探访八大关万国建筑，晚上在台东夜市品尝本地小吃。',
          activities:[
            { time_slot:'14:00-15:30', type:'attraction', title:'栈桥', subtitle:'青岛标志·百年回澜阁', description:'青岛的标志性建筑，始建于1892年，全长440米。尽头是双层八角亭"回澜阁"。', cost:0, duration_minutes:90, rating:4.5, tags:['地标','拍照','免费'], tips:'傍晚夕阳时分最美，海鸥成群', location:{lng:120.315,lat:36.062} },
            { time_slot:'15:30-17:30', type:'attraction', title:'八大关', subtitle:'万国建筑博览馆', description:'以长城八个关口命名的街区，汇聚20多个国家的建筑风格。花石楼、公主楼是代表。', cost:0, duration_minutes:120, rating:4.6, tags:['建筑','文艺','免费'], tips:'建议骑行游览', location:{lng:120.345,lat:36.052} },
            { time_slot:'18:00-21:00', type:'food', title:'台东夜市', subtitle:'青岛最大夜市中心', description:'青岛最热闹的夜市，上百个小吃摊位。', cost:80, duration_minutes:150, rating:4.4, tags:['美食','夜市','本地'], tips:'晚上6点后出摊', location:{lng:120.365,lat:36.078} },
          ],
          meals:[{ meal:'晚餐', restaurant:'王姐烧烤(台东店)', avg_price:85, reason:'烤鱿鱼和烤海肠必点' },{ meal:'宵夜', restaurant:'台东夜市小吃', avg_price:40 }],
          accommodation:{ hotel_name:'青岛栈桥海景亚朵酒店', address:'市南区太平路', room_type:'海景大床房', price:480, rating:4.7, check_in:'14:00', check_out:'12:00', location:{lng:120.318,lat:36.060} }
        },
        { day:2, date:'2026-07-21', date_label:'周二', weather_summary:'多云 30°C', day_cost:560, day_summary:'崂山一日游，看山海相连的壮丽景色，晚上去五四广场看灯光秀。',
          activities:[
            { time_slot:'07:30-15:00', type:'attraction', title:'崂山风景区(太清-仰口线)', subtitle:'海上第一名山', description:'中国海岸线第一高峰，海拔1133米。太清宫是道教全真派祖庭。', cost:120, duration_minutes:420, rating:4.7, tags:['自然','文化','登山'], tips:'带足水和干粮，穿登山鞋', location:{lng:120.629,lat:36.191} },
            { time_slot:'17:00-18:30', type:'rest', title:'石老人海水浴场', subtitle:'青岛最大海水浴场', description:'绵延3公里的金色沙滩，适合赤脚漫步赶海。', cost:0, duration_minutes:90, rating:4.3, tags:['海滨','休闲'], tips:'傍晚看不日落绝美' },
            { time_slot:'19:30-21:00', type:'entertainment', title:'五四广场·奥帆中心', subtitle:'青岛城市名片', description:'标志性雕塑"五月的风"，毗邻奥帆中心，晚上有灯光秀。', cost:0, duration_minutes:90, rating:4.5, tags:['夜景','地标','免费'], tips:'灯光秀20:00开始' },
          ],
          meals:[{ meal:'午餐', restaurant:'崂山景区农家宴', avg_price:60, reason:'崂山菇炖鸡和王哥庄大馒头' },{ meal:'晚餐', restaurant:'船歌鱼水饺(闽江路店)', avg_price:110, reason:'墨鱼水饺和鲅鱼水饺是招牌，入选非遗' }],
          accommodation:{ hotel_name:'青岛栈桥海景亚朵酒店', price:480, rating:4.7 }
        },
        { day:3, date:'2026-07-22', date_label:'周三', weather_summary:'小雨 25°C', day_cost:380, day_summary:'逛青岛啤酒博物馆品原浆，大学路网红墙打卡，下午采购特产返程。',
          activities:[
            { time_slot:'09:00-11:30', type:'attraction', title:'青岛啤酒博物馆', subtitle:'世界五大啤酒博物馆之一', description:'建于1903年的德国啤酒厂旧址。门票含原浆啤酒和啤酒豆。', cost:68, duration_minutes:150, rating:4.6, tags:['文化','体验','必去'], tips:'门票含原浆一杯+纯生一杯+啤酒豆', location:{lng:120.359,lat:36.078} },
            { time_slot:'13:00-14:30', type:'attraction', title:'大学路·鱼山路', subtitle:'青岛最文艺的转角', description:'大学路与鱼山路交叉口的红墙转角，青岛最火的网红打卡点。', cost:0, duration_minutes:90, rating:4.2, tags:['文艺','拍照','网红'], tips:'建议工作日去' },
            { time_slot:'15:00-16:30', type:'shopping', title:'中山路商业街', subtitle:'百年商业老街', description:'青岛最古老的商业街，可采购崂山绿茶、鱿鱼丝等特产。', cost:150, duration_minutes:90, rating:4.0, tags:['购物','老街'] },
            { time_slot:'17:00-18:30', type:'transport', title:'青岛站返程', subtitle:'高铁返回北京', description:'青岛站→北京南站，高铁约3小时。', cost:630, duration_minutes:150, tags:['交通','返程'] },
          ],
          meals:[{ meal:'午餐', restaurant:'波螺油子·青岛本帮菜', avg_price:75, reason:'油焖大虾和海肠捞饭' }],
        },
      ],
      weather_forecast: [
        { date:'2026-07-20', weather:'晴', temp_high:28, temp_low:22, wind:'南风3-4级', humidity:65, precipitation:0, aqi:52, advice:'适合海边活动，紫外线中等' },
        { date:'2026-07-21', weather:'多云', temp_high:30, temp_low:23, wind:'南风3级', humidity:70, precipitation:0, aqi:65, advice:'崂山登山注意补水' },
        { date:'2026-07-22', weather:'小雨', temp_high:25, temp_low:21, wind:'北风2级', humidity:82, precipitation:8, aqi:38, advice:'携带雨具，雨后八大关更清新' },
      ],
      big_traffic: {
        trains: [
          { trainCode:'G209', fromStationName:'北京南', toStationName:'青岛站', departureTime:'08:30', arrivalTime:'11:28', duration:'2h58m', prices:{'二等座':314,'一等座':504,'商务座':998} },
          { trainCode:'G211', fromStationName:'北京南', toStationName:'青岛站', departureTime:'09:15', arrivalTime:'12:22', duration:'3h07m', prices:{'二等座':314,'一等座':504} },
          { trainCode:'G1065', fromStationName:'北京南', toStationName:'青岛北', departureTime:'07:20', arrivalTime:'10:23', duration:'3h03m', prices:{'二等座':298,'一等座':478} },
        ],
        return_trains: [
          { trainCode:'G212', fromStationName:'青岛站', toStationName:'北京南', departureTime:'15:30', arrivalTime:'18:28', duration:'2h58m', prices:{'二等座':314,'一等座':504,'商务座':998} },
          { trainCode:'G108', fromStationName:'青岛站', toStationName:'北京南', departureTime:'17:05', arrivalTime:'20:12', duration:'3h07m', prices:{'二等座':314,'一等座':504} },
          { trainCode:'G206', fromStationName:'青岛北', toStationName:'北京南', departureTime:'16:00', arrivalTime:'19:03', duration:'3h03m', prices:{'二等座':298,'一等座':478} },
        ],
      },
      traffic: { daily_traffic:[
        { day:1, total_time_min:55, total_cost:24, segments:[{ from:'青岛站', to:'栈桥', mode:'步行', distance_km:0.5, time_min:5, cost:0 },{ from:'栈桥', to:'八大关', mode:'公交', distance_km:4, time_min:20, cost:2 },{ from:'八大关', to:'台东夜市', mode:'打车', distance_km:5, time_min:15, cost:15 },{ from:'台东夜市', to:'酒店', mode:'打车', distance_km:3, time_min:15, cost:7 }] },
        { day:2, total_time_min:120, total_cost:45, segments:[{ from:'酒店', to:'崂山(太清)', mode:'打车', distance_km:30, time_min:50, cost:40 },{ from:'崂山(仰口)', to:'石老人', mode:'公交', distance_km:15, time_min:40, cost:3 },{ from:'石老人', to:'五四广场', mode:'地铁', distance_km:12, time_min:20, cost:2 },{ from:'五四广场', to:'酒店', mode:'步行', distance_km:1, time_min:10, cost:0 }] },
        { day:3, total_time_min:65, total_cost:18, segments:[{ from:'酒店', to:'啤酒博物馆', mode:'步行', distance_km:0.8, time_min:8, cost:0 },{ from:'啤酒博物馆', to:'大学路', mode:'步行', distance_km:1.5, time_min:15, cost:0 },{ from:'大学路', to:'中山路', mode:'步行', distance_km:1, time_min:12, cost:0 },{ from:'中山路', to:'青岛站', mode:'步行', distance_km:0.5, time_min:5, cost:0 }] },
      ], summary:'青岛核心景点集中，步行+公交即可覆盖。', total_traffic_cost:87 },
      budget: { total_budget:5000, actual_total:4230, remaining:770, details:[
        { category:'交通', budget:1400, spent:1328, remaining:72, status:'ok' },
        { category:'住宿', budget:1400, spent:960, remaining:440, status:'ok' },
        { category:'餐饮', budget:1000, spent:870, remaining:130, status:'ok' },
        { category:'门票', budget:500, spent:288, remaining:212, status:'ok' },
        { category:'购物', budget:400, spent:150, remaining:250, status:'ok' },
        { category:'备用', budget:300, spent:0, remaining:300, status:'ok' },
      ], per_person_per_day:705 },
      hotel_plan: { recommendations:[
        { name:'青岛栈桥海景亚朵酒店', price_per_night:480, rating:4.7, address:'市南区太平路', reason:'栈桥旁海景房' },
        { name:'青岛威斯汀酒店', price_per_night:880, rating:4.8, address:'市南区香港中路', reason:'五四广场旁五星级' },
        { name:'青岛里院客栈', price_per_night:280, rating:4.3, address:'市南区中山路', reason:'百年里院改造的特色民宿' },
      ], selected:'青岛栈桥海景亚朵酒店', selected_hotel:{ name:'青岛栈桥海景亚朵酒店', price_per_night:480, rating:4.7, address:'市南区太平路' } },
      meal_plan:[
        { day:1, meals:[{ meal:'晚餐', restaurant:'王姐烧烤(台东店)', avg_price:85 },{ meal:'宵夜', restaurant:'台东夜市小吃', avg_price:40 }] },
        { day:2, meals:[{ meal:'午餐', restaurant:'崂山景区农家宴', avg_price:60 },{ meal:'晚餐', restaurant:'船歌鱼水饺(闽江路店)', avg_price:110 }] },
        { day:3, meals:[{ meal:'午餐', restaurant:'波螺油子·青岛本帮菜', avg_price:75 }] },
      ],
      attraction_details:[
        { name:'栈桥', tips:['傍晚夕阳时分最美','海鸥成群可带面包喂'], famous_spots:['回澜阁','栈桥海滨'], address:'青岛市市南区太平路14号' },
        { name:'崂山风景区(太清-仰口线)', tips:['建议早7:30前出发','带足水和干粮','穿登山鞋'], famous_spots:['太清宫','仰口索道','明霞洞'], address:'青岛市崂山区崂山风景区' },
        { name:'青岛啤酒博物馆', tips:['门票含原浆一杯+纯生一杯','醉酒小屋体验很新奇'], famous_spots:['A馆历史展厅','B馆酿造工艺','原浆品鉴区'], address:'青岛市市北区登州路56号' },
        { name:'八大关', tips:['建议骑行游览','花石楼值得入内参观'], famous_spots:['花石楼','公主楼','元帅楼'], address:'青岛市市南区八大关' },
      ],
      food_details:[
        { name:'船歌鱼水饺(闽江路店)', signature_dishes:['墨鱼水饺','鲅鱼水饺','黄花鱼水饺'] },
        { name:'王姐烧烤(台东店)', signature_dishes:['烤鱿鱼','烤海肠','烤大虾'] },
        { name:'波螺油子·青岛本帮菜', signature_dishes:['油焖大虾','海肠捞饭','辣炒蛤蜊'] },
      ],
      packing_list:['身份证','手机+充电宝','防晒霜SPF50+','遮阳帽','泳衣','沙滩拖鞋','雨伞','肠胃药(海鲜过敏)'],
      tips:['青岛啤酒按斤卖，原浆必须当天喝','海鲜推荐蒜蓉清蒸','八大关骑行是最佳游览方式','崂山建议穿登山鞋'],
      avoid_list:['不要在栈桥附近买高价水果','海景餐厅先看菜单再入座','出租车司机推荐的海鲜批发市场是陷阱','雨天不要爬崂山'],
      souvenirs:['崂山绿茶','青岛啤酒酥','鱿鱼丝','啤酒杯'],
      souvenir_recommendations:[
        { name:'崂山绿茶', description:'中国十大名茶之一', estimated_price:'¥100-300/斤', buy_place:'中山路·茶叶专卖店' },
        { name:'青岛啤酒酥', description:'以青岛啤酒为原料烘烤的酥饼', estimated_price:'¥38/盒', buy_place:'啤酒博物馆纪念品店' },
      ],
      per_person_per_day:705,
    } as any
    isGenerating.value = false
    persistCurrentPlan()
  }

  function loadTestPlanWuhan(): void {
    currentPlan.value = {
      id: 'test_wuhan', title: '武汉4日人文之旅', destination: '武汉', departure: '上海',
      start_date: '2026-08-10', end_date: '2026-08-13', days: 4, people_count: 1,
      crowd_type: '独自旅行', total_budget: 3500, estimated_cost: 2980,
      travel_style: '人文探索', status: 'completed', version: 1, is_favorite: true,
      view_count: 34, pace: '紧凑',
      trip_config: { pace: '紧凑', travelers: 1, preferences: ['人文', '历史'] },
      overview: { highlights: ['黄鹤楼-长江大桥-户部巷经典一线','湖北省博物馆越王勾践剑','武汉大学民国建筑群','东湖绿道骑行体验','粮道街过早·热干面蛋酒'], total_distance_km: 45, transport_modes: ['地铁','公交','共享单车'] },
      daily_itinerary: [
        { day:1, date:'2026-08-10', date_label:'周二', weather_summary:'晴 35°C', day_cost:350, day_summary:'抵达武汉，下午逛江汉路步行街，晚上吉庆街夜市。',
          activities:[
            { time_slot:'14:00-17:00', type:'attraction', title:'江汉路步行街', subtitle:'中国最长步行街', description:'全长1600米，百年商业老街。', cost:0, duration_minutes:180, rating:4.3, tags:['购物','建筑'] },
            { time_slot:'18:00-21:00', type:'food', title:'吉庆街夜市', subtitle:'武汉最接地气的夜市', description:'武汉最有烟火气的夜市。', cost:80, duration_minutes:150, rating:4.5, tags:['美食','夜市'] },
          ],
          meals:[{ meal:'晚餐', restaurant:'小民大排档(吉庆街)', avg_price:80, reason:'油焖大虾和凉拌毛豆' }],
        },
        { day:2, date:'2026-08-11', date_label:'周三', weather_summary:'多云 33°C', day_cost:420, day_summary:'登黄鹤楼俯瞰长江，参观省博看越王勾践剑。',
          activities:[
            { time_slot:'08:00-10:30', type:'attraction', title:'黄鹤楼', subtitle:'天下江山第一楼', description:'武汉最著名的地标，始建于三国时期。', cost:70, duration_minutes:150, rating:4.5, tags:['文化','历史','地标'] },
            { time_slot:'11:00-13:00', type:'attraction', title:'湖北省博物馆', subtitle:'国家级首批博物馆', description:'馆藏文物24万件，四大镇馆之宝。', cost:0, duration_minutes:120, rating:4.8, tags:['文化','历史','必去'], tips:'免费需提前预约，周一闭馆' },
            { time_slot:'18:00-21:00', type:'food', title:'户部巷', subtitle:'汉味早点第一巷', description:'武汉最有名的小吃街。', cost:60, duration_minutes:120, rating:4.2, tags:['美食','老街'] },
          ],
          meals:[{ meal:'午餐', restaurant:'亢龙太子酒轩', avg_price:90, reason:'清蒸武昌鱼和排骨藕汤' },{ meal:'晚餐', restaurant:'蔡林记(户部巷店)', avg_price:25, reason:'最正宗的热干面配蛋酒' }],
        },
        { day:3, date:'2026-08-12', date_label:'周四', weather_summary:'多云 32°C', day_cost:380, day_summary:'武汉大学人文漫步，东湖绿道骑行。',
          activities:[
            { time_slot:'09:00-12:00', type:'attraction', title:'武汉大学', subtitle:'中国最美大学之一', description:'珞珈山麓，东湖之滨。民国建筑群是核心看点。', cost:0, duration_minutes:180, rating:4.6, tags:['校园','建筑','文艺'] },
            { time_slot:'14:00-17:00', type:'entertainment', title:'东湖绿道', subtitle:'世界级城市绿道', description:'全长102公里，骑行是最佳方式。', cost:30, duration_minutes:180, rating:4.7, tags:['户外','骑行','免费'] },
            { time_slot:'18:00-21:00', type:'shopping', title:'楚河汉街', subtitle:'武汉最潮商业街', description:'民国风格商业街，品牌店密集。', cost:100, duration_minutes:150, rating:4.3, tags:['购物','夜景'] },
          ],
          meals:[{ meal:'午餐', restaurant:'武大食堂(对外开放)', avg_price:25 },{ meal:'晚餐', restaurant:'老村长私募菜', avg_price:85, reason:'排骨藕汤和粉蒸肉' }],
        },
        { day:4, date:'2026-08-13', date_label:'周五', weather_summary:'晴 34°C', day_cost:320, day_summary:'古琴台+晴川阁，下午返程。',
          activities:[
            { time_slot:'09:00-11:00', type:'attraction', title:'古琴台', subtitle:'伯牙绝弦之地', description:'纪念俞伯牙和钟子期知音故事。', cost:15, duration_minutes:120, rating:4.1, tags:['文化','历史'] },
            { time_slot:'11:30-13:00', type:'attraction', title:'晴川阁', subtitle:'楚天第一名楼', description:'与黄鹤楼隔江相望，建于明代。', cost:0, duration_minutes:90, rating:4.3, tags:['文化','历史','免费'] },
            { time_slot:'17:30-19:00', type:'transport', title:'武汉站返程', subtitle:'高铁返回上海', description:'武汉站→上海虹桥，高铁约4.5小时。', cost:510, duration_minutes:150, tags:['交通','返程'] },
          ],
          meals:[{ meal:'午餐', restaurant:'归元寺素菜馆', avg_price:40 },{ meal:'晚餐', restaurant:'武汉站餐饮', avg_price:45 }],
        },
      ],
      weather_forecast: [
        { date:'2026-08-10', weather:'晴', temp_high:35, temp_low:28, wind:'南风2级', humidity:60, advice:'高温注意防暑' },
        { date:'2026-08-11', weather:'多云', temp_high:33, temp_low:26, wind:'东风2级', humidity:65, advice:'适宜出行' },
      ],
      big_traffic: {
        trains:[
          { trainCode:'G1728', fromStationName:'上海虹桥', toStationName:'武汉站', departureTime:'08:00', arrivalTime:'12:27', duration:'4h27m', prices:{'二等座':510,'一等座':815} },
          { trainCode:'G1730', fromStationName:'上海虹桥', toStationName:'武汉站', departureTime:'13:00', arrivalTime:'17:36', duration:'4h36m', prices:{'二等座':510,'一等座':815} },
        ],
        return_trains:[
          { trainCode:'G1727', fromStationName:'武汉站', toStationName:'上海虹桥', departureTime:'07:30', arrivalTime:'12:02', duration:'4h32m', prices:{'二等座':510,'一等座':815} },
          { trainCode:'G1739', fromStationName:'武汉站', toStationName:'上海虹桥', departureTime:'14:50', arrivalTime:'19:21', duration:'4h31m', prices:{'二等座':510,'一等座':815} },
        ],
      },
      traffic: { daily_traffic:[
        { day:1, total_time_min:45, total_cost:16, segments:[{ from:'武汉站', to:'江汉路', mode:'地铁', distance_km:15, time_min:35, cost:6 },{ from:'江汉路', to:'吉庆街', mode:'步行', distance_km:0.5, time_min:5, cost:0 }] },
        { day:2, total_time_min:60, total_cost:22, segments:[{ from:'酒店', to:'黄鹤楼', mode:'公交', distance_km:4, time_min:20, cost:2 },{ from:'黄鹤楼', to:'省博', mode:'地铁', distance_km:8, time_min:25, cost:5 },{ from:'省博', to:'户部巷', mode:'打车', distance_km:6, time_min:15, cost:15 }] },
        { day:3, total_time_min:40, total_cost:10, segments:[{ from:'酒店', to:'武大', mode:'公交', distance_km:5, time_min:20, cost:2 },{ from:'武大', to:'东湖绿道', mode:'步行', distance_km:0.5, time_min:5, cost:0 },{ from:'东湖磨山', to:'楚河汉街', mode:'打车', distance_km:8, time_min:15, cost:8 }] },
        { day:4, total_time_min:80, total_cost:28, segments:[{ from:'酒店', to:'古琴台', mode:'公交', distance_km:3, time_min:15, cost:2 },{ from:'古琴台', to:'晴川阁', mode:'步行', distance_km:0.3, time_min:3, cost:0 },{ from:'晴川阁', to:'归元寺', mode:'打车', distance_km:6, time_min:15, cost:14 },{ from:'归元寺', to:'武汉站', mode:'地铁', distance_km:18, time_min:35, cost:7 }] },
      ], summary:'武汉地铁覆盖率极高，建议全程地铁+共享单车。', total_traffic_cost:76 },
      budget: { total_budget:3500, actual_total:2980, remaining:520, details:[
        { category:'交通', budget:1200, spent:1126, remaining:74, status:'ok' },
        { category:'住宿', budget:1000, spent:880, remaining:120, status:'ok' },
        // 没有餐饮分类（验证 ¥0 不显示）
        { category:'门票', budget:300, spent:205, remaining:95, status:'ok' },
        { category:'购物', budget:500, spent:350, remaining:150, status:'ok' },
        { category:'备用', budget:500, spent:0, remaining:500, status:'ok' },
      ], per_person_per_day:745 },
      hotel_plan: { recommendations:[
        { name:'武汉江汉路亚朵酒店', price_per_night:380, rating:4.6, address:'江汉区江汉路' },
        { name:'武汉万达瑞华酒店', price_per_night:980, rating:4.9, address:'武昌区楚河汉街' },
      ] },
      per_person_per_day:745,
    } as any
    isGenerating.value = false
    persistCurrentPlan()
  }

  function loadTestPlanXian(): void {
    currentPlan.value = {
      id: 'test_xian', title: '西安5日深度文化游', destination: '西安', departure: '北京',
      start_date: '2026-09-15', end_date: '2026-09-19', days: 5, people_count: 2,
      crowd_type: '朋友/情侣', total_budget: 6000, estimated_cost: 6820,
      travel_style: '文化深度', status: 'completed', version: 1, is_favorite: false,
      view_count: 128, pace: '紧凑',
      trip_config: { pace: '紧凑', travelers: 2, preferences: ['文化','历史','美食'] },
      overview: { highlights:['兵马俑一号坑千人千面震撼','华山长空栈道险峻体验','不夜城大唐盛世穿越感','回民街羊肉泡馍biangbiang面','陕西历史博物馆周秦汉唐国宝'], total_distance_km:180, transport_modes:['地铁','打车','高铁','索道'] },
      daily_itinerary: [
        { day:1, date:'2026-09-15', date_label:'周三', weather_summary:'晴 36°C', day_cost:580, day_summary:'抵达西安，下午游城墙骑行，晚上大唐不夜城看灯光秀。',
          activities:[
            { time_slot:'14:00-16:30', type:'attraction', title:'西安城墙', subtitle:'中国现存最完整古城墙', description:'全长13.7公里，可骑行(¥45)或步行游览。', cost:54, duration_minutes:150, rating:4.6, tags:['文化','历史','骑行'], tips:'建议永宁门上', location:{lng:108.942,lat:34.256} },
            { time_slot:'17:00-18:30', type:'attraction', title:'钟楼·鼓楼', subtitle:'西安城市中心地标', description:'钟楼位于城市正中央，鼓楼上有巨鼓一面。', cost:50, duration_minutes:90, rating:4.4, tags:['地标','文化'] },
            { time_slot:'19:00-21:30', type:'entertainment', title:'大唐不夜城', subtitle:'西安最火爆的夜游地', description:'南北长2100米的步行街，各种灯光秀、唐风表演。', cost:0, duration_minutes:150, rating:4.7, tags:['夜景','文化','网红'], tips:'19:00后灯光亮起最佳' },
          ],
          meals:[{ meal:'晚餐', restaurant:'长安大排档(赛格店)', avg_price:95, reason:'毛笔酥和葫芦鸡必点' },{ meal:'宵夜', restaurant:'大唐不夜城小吃', avg_price:40 }],
          accommodation:{ hotel_name:'西安钟楼诺富特酒店', address:'碑林区南大街', room_type:'高级双床房', price:420, rating:4.5, check_in:'14:00', check_out:'12:00', location:{lng:108.942,lat:34.257} }
        },
        { day:2, date:'2026-09-16', date_label:'周四', weather_summary:'多云 34°C', day_cost:1250, day_summary:'华山一日挑战，体验长空栈道。',
          activities:[
            { time_slot:'06:30-17:00', type:'attraction', title:'华山', subtitle:'五岳之险·奇险天下第一山', description:'西峰索道上北峰索道下，全程约8-10小时。长空栈道最刺激。', cost:360, duration_minutes:540, rating:4.9, tags:['登山','自然','挑战'], tips:'西峰索道上北峰索道下最省力', location:{lng:110.089,lat:34.476} },
          ],
          meals:[{ meal:'午餐', restaurant:'华山北峰餐厅', avg_price:45 },{ meal:'晚餐', restaurant:'西安饭庄(钟楼店)', avg_price:110, reason:'稠酒和泡泡油糕' }],
          accommodation:{ hotel_name:'西安钟楼诺富特酒店', price:420, rating:4.5 }
        },
        { day:3, date:'2026-09-17', date_label:'周五', weather_summary:'小雨 28°C', day_cost:380, day_summary:'兵马俑一日穿越秦朝，晚上回民街美食之旅。',
          activities:[
            { time_slot:'08:00-12:00', type:'attraction', title:'秦始皇兵马俑博物馆', subtitle:'世界第八大奇迹', description:'一号坑上千个真人大小陶俑排列成军阵，千人千面。', cost:120, duration_minutes:240, rating:4.9, tags:['历史','世界遗产','必去'], tips:'建议早上8点开门就进', location:{lng:109.277,lat:34.385} },
            { time_slot:'14:00-16:00', type:'attraction', title:'华清宫', subtitle:'唐玄宗与杨贵妃爱情地', description:'唐代皇家离宫，西安事变发生地。', cost:120, duration_minutes:120, rating:4.3, tags:['历史','文化'] },
            { time_slot:'18:00-21:00', type:'food', title:'回民街', subtitle:'西安最著名美食街', description:'老米家大雨泡馍、定家小酥肉、贾三灌汤包。', cost:80, duration_minutes:150, rating:4.4, tags:['美食','老街','夜市'], tips:'洒金桥才是本地人的选择' },
          ],
          meals:[{ meal:'午餐', restaurant:'临潼农家乐', avg_price:55, reason:'关中蒸碗和石子馍' },{ meal:'晚餐', restaurant:'老米家大雨泡馍(回民街)', avg_price:45, reason:'自己掰馍更有仪式感' }],
          accommodation:{ hotel_name:'西安钟楼诺富特酒店', price:420, rating:4.5 }
        },
        { day:4, date:'2026-09-18', date_label:'周六', weather_summary:'中雨 25°C', day_cost:820, day_summary:'陕博看国宝，大雁塔登高，晚上看长恨歌演出。',
          activities:[
            { time_slot:'09:00-12:30', type:'attraction', title:'陕西历史博物馆', subtitle:'给我一天还你万年', description:'馆藏171万件，周秦汉唐四朝文物精华。', cost:30, duration_minutes:210, rating:4.8, tags:['文化','历史','必去'], tips:'免费票需提前3天预约', location:{lng:108.957,lat:34.218} },
            { time_slot:'14:00-16:00', type:'attraction', title:'大雁塔', subtitle:'玄奘译经之处', description:'塔高64米，共7层。登塔可俯瞰西安古城全景。', cost:85, duration_minutes:120, rating:4.5, tags:['宗教','文化','历史'] },
            { time_slot:'20:00-21:30', type:'entertainment', title:'长恨歌演出', subtitle:'中国首部大型实景历史舞剧', description:'在华清宫上演，山水实景、300名演员。', cost:358, duration_minutes:90, rating:4.9, tags:['演出','文化','必看'], tips:'提前3天以上订票' },
          ],
          meals:[{ meal:'午餐', restaurant:'子午路张记肉夹馍', avg_price:30, reason:'西安最好吃的肉夹馍' },{ meal:'晚餐', restaurant:'醉长安(钟楼店)', avg_price:95, reason:'晾衣毛肚和桂花凉糕' }],
          accommodation:{ hotel_name:'西安钟楼诺富特酒店', price:420, rating:4.5 }
        },
        { day:5, date:'2026-09-19', date_label:'周日', weather_summary:'阴 27°C', day_cost:480, day_summary:'上午小雁塔，采购特产返程。',
          activities:[
            { time_slot:'09:00-11:00', type:'attraction', title:'小雁塔·西安博物院', subtitle:'关中八景之一', description:'小雁塔建于唐景龙年间，比大雁塔小巧更古朴。', cost:0, duration_minutes:120, rating:4.3, tags:['文化','历史','免费'] },
            { time_slot:'11:30-13:30', type:'shopping', title:'书院门文化街', subtitle:'笔墨纸砚老街', description:'售卖文房四宝、碑帖拓片、剪纸皮影。', cost:200, duration_minutes:120, rating:4.0, tags:['购物','文化'] },
            { time_slot:'14:00-15:30', type:'attraction', title:'碑林博物馆', subtitle:'中国书法艺术宝库', description:'收藏历代碑石墓志3000余方。', cost:50, duration_minutes:90, rating:4.6, tags:['文化','书法'] },
            { time_slot:'16:30-18:00', type:'transport', title:'西安北站返程', subtitle:'高铁返回北京', description:'西安北站→北京西站，高铁约4.5小时。', cost:516, duration_minutes:150, tags:['交通','返程'] },
          ],
          meals:[{ meal:'午餐', restaurant:'秦豫肉夹馍(东木头市店)', avg_price:35 }],
        },
      ],
      weather_forecast: [
        { date:'2026-09-15', weather:'晴', temp_high:36, temp_low:24, wind:'东北风2级', humidity:45, precipitation:0, aqi:85, advice:'高温预警！注意防暑降温' },
        { date:'2026-09-16', weather:'多云', temp_high:34, temp_low:22, wind:'东风3级', humidity:50, precipitation:0, aqi:72, advice:'华山紫外线强' },
        { date:'2026-09-17', weather:'小雨', temp_high:28, temp_low:19, wind:'西风2级', humidity:78, precipitation:12, aqi:42, advice:'携带雨具' },
        { date:'2026-09-18', weather:'中雨', temp_high:25, temp_low:18, wind:'西南风3级', humidity:85, precipitation:25, aqi:35, advice:'长恨歌如遇大雨可能取消' },
        { date:'2026-09-19', weather:'阴', temp_high:27, temp_low:20, wind:'北风2级', humidity:60, precipitation:0, aqi:55, advice:'返程日天气良好' },
      ],
      big_traffic: {
        trains:[
          { trainCode:'G655', fromStationName:'北京西', toStationName:'西安北', departureTime:'08:00', arrivalTime:'12:24', duration:'4h24m', prices:{'二等座':516,'一等座':826,'商务座':1636} },
          { trainCode:'G659', fromStationName:'北京西', toStationName:'西安北', departureTime:'09:15', arrivalTime:'13:52', duration:'4h37m', prices:{'二等座':516,'一等座':826} },
          { trainCode:'G665', fromStationName:'北京西', toStationName:'西安北', departureTime:'06:40', arrivalTime:'11:08', duration:'4h28m', prices:{'二等座':516,'一等座':826} },
        ],
        return_trains:[
          { trainCode:'G656', fromStationName:'西安北', toStationName:'北京西', departureTime:'13:00', arrivalTime:'17:22', duration:'4h22m', prices:{'二等座':516,'一等座':826,'商务座':1636} },
          { trainCode:'G662', fromStationName:'西安北', toStationName:'北京西', departureTime:'14:35', arrivalTime:'19:08', duration:'4h33m', prices:{'二等座':516,'一等座':826} },
          { trainCode:'G670', fromStationName:'西安北', toStationName:'北京西', departureTime:'17:00', arrivalTime:'21:24', duration:'4h24m', prices:{'二等座':516,'一等座':826} },
        ],
      },
      traffic: { daily_traffic:[
        { day:1, total_time_min:60, total_cost:28, segments:[{ from:'西安北站', to:'钟楼', mode:'地铁', distance_km:12, time_min:30, cost:5 },{ from:'钟楼', to:'永宁门', mode:'步行', distance_km:0.5, time_min:5, cost:0 },{ from:'永宁门', to:'大雁塔', mode:'地铁', distance_km:6, time_min:20, cost:3 },{ from:'大雁塔', to:'酒店', mode:'打车', distance_km:3, time_min:10, cost:12 }] },
        { day:2, total_time_min:210, total_cost:280, segments:[{ from:'酒店', to:'西安北站', mode:'打车', distance_km:12, time_min:25, cost:20 },{ from:'西安北站', to:'华山北站', mode:'高铁', distance_km:120, time_min:35, cost:110 },{ from:'华山北站', to:'华山游客中心', mode:'免费摆渡车', distance_km:5, time_min:10, cost:0 },{ from:'华山游客中心', to:'西峰索道', mode:'景区巴士', distance_km:20, time_min:40, cost:40 },{ from:'华山北峰索道', to:'华山北站', mode:'摆渡车', distance_km:5, time_min:10, cost:0 },{ from:'华山北站', to:'西安北站', mode:'高铁', distance_km:120, time_min:35, cost:110 },{ from:'西安北站', to:'酒店', mode:'地铁', distance_km:12, time_min:30, cost:5 }] },
        { day:3, total_time_min:110, total_cost:85, segments:[{ from:'酒店', to:'兵马俑', mode:'地铁+公交', distance_km:40, time_min:60, cost:20 },{ from:'兵马俑', to:'华清宫', mode:'公交', distance_km:5, time_min:15, cost:3 },{ from:'华清宫', to:'回民街', mode:'地铁+公交', distance_km:35, time_min:50, cost:15 }] },
        { day:4, total_time_min:90, total_cost:45, segments:[{ from:'酒店', to:'陕博', mode:'步行', distance_km:1, time_min:10, cost:0 },{ from:'陕博', to:'大雁塔', mode:'步行', distance_km:1.5, time_min:15, cost:0 },{ from:'大雁塔', to:'芙蓉园', mode:'步行', distance_km:0.8, time_min:8, cost:0 },{ from:'芙蓉园', to:'华清宫', mode:'打车', distance_km:35, time_min:40, cost:50 }] },
        { day:5, total_time_min:65, total_cost:22, segments:[{ from:'酒店', to:'小雁塔', mode:'地铁', distance_km:5, time_min:20, cost:4 },{ from:'小雁塔', to:'书院门', mode:'步行', distance_km:2, time_min:15, cost:0 },{ from:'书院门', to:'碑林', mode:'步行', distance_km:0.3, time_min:3, cost:0 },{ from:'碑林', to:'西安北站', mode:'地铁', distance_km:15, time_min:35, cost:6 }] },
      ], summary:'西安景点分散，东线需一天，华山往返需高铁+索道。', total_traffic_cost:460 },
      budget: { total_budget:6000, actual_total:6820, remaining:-820, details:[
        { category:'交通', budget:1500, spent:1580, remaining:-80, status:'over' },
        { category:'住宿', budget:1600, spent:1680, remaining:-80, status:'over' },
        { category:'餐饮', budget:1000, spent:850, remaining:150, status:'ok' },
        { category:'门票', budget:1200, spent:1379, remaining:-179, status:'over' },
        { category:'购物', budget:400, spent:350, remaining:50, status:'ok' },
        { category:'备用', budget:300, spent:0, remaining:300, status:'ok' },
      ], per_person_per_day:682, warnings:[
        '总预算¥6000，已超支¥820（13.7%），建议压缩门票或餐饮开支',
        '华山+长恨歌演出一天花费¥1270，占总预算21%',
        '交通费超支¥80，因华山往返高铁额外支出',
      ], suggestions:[
        { action:'华山西峰索道改为北峰索道上下', save:120 },
        { action:'长恨歌演出票选择中区¥358而非VIP区¥998', save:640 },
        { action:'住宿选择民宿而非品牌酒店，可省¥100/晚', save:400 },
        { action:'陕博免费票提前预约，可省¥30/人', save:60 },
      ]},
      hotel_plan: { recommendations:[
        { name:'西安钟楼诺富特酒店', price_per_night:420, rating:4.5, address:'碑林区南大街', reason:'钟楼旁核心位置' },
        { name:'西安威斯汀酒店', price_per_night:780, rating:4.7, address:'雁塔区大雁塔南广场', reason:'大雁塔旁五星级' },
        { name:'西安湘子门青旅', price_per_night:120, rating:4.2, address:'南门湘子庙街', reason:'古城内特色青旅' },
        { name:'西安索菲特传奇酒店', price_per_night:1580, rating:4.9, address:'新城区东新街', reason:'奢华法式风情' },
      ], selected:'西安钟楼诺富特酒店', selected_hotel:{ name:'西安钟楼诺富特酒店', price_per_night:420, rating:4.5, address:'碑林区南大街' } },
      meal_plan:[
        { day:1, meals:[{ meal:'晚餐', restaurant:'长安大排档', avg_price:95 },{ meal:'宵夜', restaurant:'不夜城小吃', avg_price:40 }] },
        { day:2, meals:[{ meal:'午餐', restaurant:'华山北峰餐厅', avg_price:45 },{ meal:'晚餐', restaurant:'西安饭庄', avg_price:110 }] },
        { day:3, meals:[{ meal:'午餐', restaurant:'临潼农家乐', avg_price:55 },{ meal:'晚餐', restaurant:'老米家大雨泡馍', avg_price:45 }] },
        { day:4, meals:[{ meal:'午餐', restaurant:'子午路张记肉夹馍', avg_price:30 },{ meal:'晚餐', restaurant:'醉长安', avg_price:95 }] },
        { day:5, meals:[{ meal:'午餐', restaurant:'秦豫肉夹馍', avg_price:35 }] },
      ],
      attraction_details:[
        { name:'西安城墙', tips:['永宁门是最壮观的登城入口','骑行全程13.7km约2小时'], famous_spots:['永宁门','长乐门','安定门'], address:'西安市碑林区南大街' },
        { name:'华山', tips:['西峰索道上北峰索道下最省力','长空栈道¥30另付'], famous_spots:['西峰索道','长空栈道','东峰观日台'], address:'渭南市华阴市华山风景区' },
        { name:'秦始皇兵马俑博物馆', tips:['建议早8点开门就进','请导游讲解体验更好'], famous_spots:['一号坑','二号坑','三号坑','铜车马展厅'], address:'西安市临潼区秦陵北路' },
        { name:'陕西历史博物馆', tips:['免费票提前3天预约','周一闭馆'], famous_spots:['鎏金舞马衔杯银壶','镶金兽首玛瑙杯'], address:'西安市雁塔区小寨东路91号' },
        { name:'碑林博物馆', tips:['建议请讲解不然看不懂','拓片体验¥20起'], famous_spots:['颜真卿颜氏家庙碑','怀素草书千字文'], address:'西安市碑林区三学街15号' },
      ],
      food_details:[
        { name:'长安大排档(赛格店)', signature_dishes:['毛笔酥','葫芦鸡','长安烤鸭','醪糟冰淇淋'] },
        { name:'老米家大雨泡馍(回民街)', signature_dishes:['羊肉泡馍','牛肉小炒','糖蒜'] },
        { name:'子午路张记肉夹馍', signature_dishes:['优质肉夹馍','凉皮','冰峰汽水'] },
        { name:'西安饭庄(钟楼店)', signature_dishes:['稠酒','泡泡油糕','金线油塔','葫芦鸡'] },
      ],
      packing_list:['身份证','手机+充电宝','防晒霜SPF50+','遮阳帽','登山鞋(华山用)','薄外套(华山顶用)','雨伞(9月多雨)','肠胃药(陕西辣)','学生证(门票优惠)'],
      tips:['兵马俑建议8:00开门就进，避开10:00后旅行团高峰','华山西峰索道上北峰索道下是最佳路线','回民街主街游客多，旁边洒金桥才是本地人选择','长恨歌提前3天以上订票'],
      avoid_list:['不要在兵马俑景区买玉器，99%是假货','回民街不要吃海鲜，不新鲜','华山雨天不要走长空栈道','景区附近免费导游最终会带你去购物店'],
      souvenirs:['碑帖拓片','仿唐三彩','皮影','贵妃酥','琼锅糖'],
      souvenir_recommendations:[
        { name:'碑帖拓片', description:'碑林名碑的拓片复制品', estimated_price:'¥20-200/张', buy_place:'书院门文化街' },
        { name:'仿唐三彩', description:'唐代陶器经典造型', estimated_price:'¥50-300/件', buy_place:'书院门·唐工艺品店' },
        { name:'皮影', description:'陕西非遗，牛皮雕刻染色制成', estimated_price:'¥30-150/个', buy_place:'回民街·皮影店' },
      ],
      per_person_per_day:682,
    } as any
    isGenerating.value = false
    persistCurrentPlan()
  }

  /** 加载测试方案列表数据（PlanCard 渲染验证） */
  function loadTestPlanList(): void {
    plans.value = [
      { id: 'test_plan_1', title: '长沙7日深度游', destination: '长沙', days: 7, estimated_cost: 3932, start_date: '2026-07-10', end_date: '2026-07-16', travel_style: 'relaxed', status: 'completed', is_favorite: true, created_at: '2026-07-09T10:00:00Z' },
      { id: 'test_plan_2', title: '北京3日文化之旅', destination: '北京', days: 3, estimated_cost: 2140, start_date: '2026-08-05', end_date: '2026-08-07', travel_style: 'culture', status: 'completed', is_favorite: false, created_at: '2026-07-08T14:30:00Z' },
      { id: 'test_plan_3', title: '成都美食5日行', destination: '成都', days: 5, estimated_cost: 3200, start_date: '2026-08-15', end_date: '2026-08-19', travel_style: 'food', status: 'completed', is_favorite: false, created_at: '2026-07-07T09:15:00Z' },
      { id: 'test_plan_4', title: '杭州4日休闲游', destination: '杭州', days: 4, estimated_cost: 4400, start_date: '2026-09-01', end_date: '2026-09-04', travel_style: 'relaxed', status: 'completed', is_favorite: true, created_at: '2026-07-06T11:20:00Z' },
      { id: 'test_plan_5', title: '西安3日探险之旅', destination: '西安', days: 3, estimated_cost: 1820, start_date: '2026-09-20', end_date: '2026-09-22', travel_style: 'adventure', status: 'completed', is_favorite: false, created_at: '2026-07-05T16:45:00Z' },
      { id: 'test_plan_6', title: '厦门5日海滨假日', destination: '厦门', days: 5, estimated_cost: 5700, start_date: '2026-10-01', end_date: '2026-10-05', travel_style: 'relaxed', status: 'completed', is_favorite: false, created_at: '2026-07-04T08:30:00Z' },
      { id: 'test_plan_7', title: '云南8日全景环游', destination: '昆明/大理/丽江', days: 8, estimated_cost: 6800, start_date: '2026-10-15', end_date: '2026-10-22', travel_style: 'intensive', status: 'completed', is_favorite: false, created_at: '2026-07-03T13:10:00Z' },
      { id: 'test_plan_8', title: '重庆3日山城探索', destination: '重庆', days: 3, estimated_cost: 1560, start_date: '2026-11-01', end_date: '2026-11-03', travel_style: 'adventure', status: 'completed', is_favorite: true, created_at: '2026-07-02T10:50:00Z' },
      { id: 'test_plan_9', title: '三亚7日滨海度假', destination: '三亚', days: 7, estimated_cost: 8200, start_date: '2026-11-20', end_date: '2026-11-26', travel_style: 'relaxed', status: 'draft', is_favorite: false, created_at: '2026-07-01T09:00:00Z' },
    ] as any
    total.value = plans.value.length
  }


  return {
    // state
    plans,
    total,
    currentPlan,
    isGenerating,
    isModifying,
    generateProgress,
    exportTask,
    // actions
    fetchPlans,
    fetchPlanDetail,
    updateProgress,
    modifyPlan,
    deletePlan,
    regeneratePlan,
    exportPlan,
    pollExportTask,
    exportImage,
    exportPdf,
    exportDocx,
    sharePlan,
    toggleFavorite,
    clearCurrentPlan,
    persistCurrentPlan,
    clearPlanCache,
    restoreCachedPlan,
    mapSSESummaryToPlan,
    normalizeSSESummary,
    loadTestPlan,
    loadTestPlanChengdu,
    loadTestPlanBeijing,
    loadTestPlanQingdao,
    loadTestPlanWuhan,
    loadTestPlanXian,
    loadTestPlanList,
  }
})
