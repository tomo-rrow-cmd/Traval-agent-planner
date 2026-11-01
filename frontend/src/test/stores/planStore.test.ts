import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { resolveExportFilename, usePlanStore } from '@/store/planStore'

vi.mock('@/api/plan', () => ({
  getPlans: vi.fn(),
  getPlanDetail: vi.fn(),
  modifyPlan: vi.fn(),
  deletePlan: vi.fn(),
  exportPlan: vi.fn(),
  sharePlan: vi.fn(),
  toggleFavorite: vi.fn(),
}))

import {
  getPlans as apiGetPlans,
  getPlanDetail as apiGetPlanDetail,
  deletePlan as apiDeletePlan,
  toggleFavorite as apiToggleFavorite,
} from '@/api/plan'
import { mockPlanListResponse, mockPlanDetailResponse, mockFavoriteToggleResponse } from '@/test/mocks/plan'

describe('planStore 数据流', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  describe('导出文件名', () => {
    it('应优先解析 RFC 5987 中文文件名', () => {
      const filename = resolveExportFilename(
        'attachment; filename="export.pdf"; filename*=UTF-8\'\'%E5%8C%97%E4%BA%AC3%E6%97%A5%E6%B8%B8.pdf',
        'application/pdf',
      )

      expect(filename).toBe('北京3日游.pdf')
    })

    it('响应头缺失时仍应按 MIME 返回正确扩展名', () => {
      expect(resolveExportFilename('', 'application/pdf', '北京旅行')).toBe('北京旅行.pdf')
    })
  })

  describe('方案列表', () => {
    it('应正确获取方案列表', async () => {
      const store = usePlanStore()
      vi.mocked(apiGetPlans).mockResolvedValue({ data: mockPlanListResponse } as any)

      await store.fetchPlans()

      expect(store.plans).toHaveLength(3)
      expect(store.plans[0].destination).toBe('云南大理')
      expect(store.plans[0].days).toBe(5)
      expect(store.plans[1].is_favorite).toBe(true)
    })
  })

  describe('方案详情', () => {
    it('应正确获取方案详情并填充 currentPlan', async () => {
      const store = usePlanStore()
      vi.mocked(apiGetPlanDetail).mockResolvedValue({ data: mockPlanDetailResponse } as any)

      await store.fetchPlanDetail('plan_mock001')

      expect(store.currentPlan).toBeDefined()
      expect(store.currentPlan?.destination).toBe('云南大理')
      expect(store.currentPlan?.daily_itinerary).toHaveLength(2)
      expect(store.currentPlan?.daily_itinerary[0].activities).toHaveLength(3)
      expect(store.currentPlan?.budget_detail?.total).toBe(4500)
    })

    it('应正确解析方案详情中的活动类型', async () => {
      const store = usePlanStore()
      vi.mocked(apiGetPlanDetail).mockResolvedValue({ data: mockPlanDetailResponse } as any)

      await store.fetchPlanDetail('plan_mock001')

      const day1 = store.currentPlan!.daily_itinerary[0]
      expect(day1.activities[0].type).toBe('attraction')
      expect(day1.activities[1].type).toBe('food')
      expect(day1.activities[2].type).toBe('shopping')
    })
  })

  describe('SSE 摘要映射', () => {
    it('应正确将 SSE done 事件的 summary 映射为 Partial<PlanResponse>', () => {
      const store = usePlanStore()

      const sseSummary = {
        destination: '云南大理',
        days: 5,
        daily_plan: [
          {
            day: 1,
            date: '2026-07-15',
            title: 'Day 1',
            theme: '',
            activities: [],
          },
        ],
        meal_plan: [],
        hotel_plan: { recommendations: [] },
        traffic: { daily_plan: [], total_traffic_cost: 300 },
        budget: { total: 4500, breakdown: {}, remaining: 500 },
        souvenirs: [],
      }

      const plan = store.mapSSESummaryToPlan(sseSummary)

      expect(plan).toBeDefined()
      expect(plan?.destination).toBe('云南大理')
      expect(plan?.days).toBe(5)
      expect(plan?.daily_itinerary).toHaveLength(1)
    })

    it('null summary 应返回 null', () => {
      const store = usePlanStore()
      const result = store.mapSSESummaryToPlan(null)
      expect(result).toBeNull()
    })
  })

  describe('收藏切换', () => {
    it('应正确切换收藏状态', async () => {
      const store = usePlanStore()
      vi.mocked(apiGetPlans).mockResolvedValue({ data: mockPlanListResponse } as any)
      vi.mocked(apiToggleFavorite).mockResolvedValue({ data: mockFavoriteToggleResponse } as any)

      await store.fetchPlans()
      const result = await store.toggleFavorite('plan_mock001')

      expect(result.is_favorite).toBe(true)
      expect(store.plans[0].is_favorite).toBe(true)
    })
  })

  describe('删除方案', () => {
    it('删除后应从列表中移除', async () => {
      const store = usePlanStore()
      vi.mocked(apiGetPlans).mockResolvedValue({ data: mockPlanListResponse } as any)
      vi.mocked(apiDeletePlan).mockResolvedValue({ data: { code: 0, message: '', data: {} } } as any)

      await store.fetchPlans()
      expect(store.plans).toHaveLength(3)

      await store.deletePlan('plan_mock001')
      expect(store.plans).toHaveLength(2)
      expect(store.plans.find((p: any) => p.id === 'plan_mock001')).toBeUndefined()
    })

    it('删除当前查看的方案应清空 currentPlan', async () => {
      const store = usePlanStore()
      vi.mocked(apiGetPlanDetail).mockResolvedValue({ data: mockPlanDetailResponse } as any)
      vi.mocked(apiDeletePlan).mockResolvedValue({ data: { code: 0, message: '', data: {} } } as any)

      await store.fetchPlanDetail('plan_mock001')
      await store.deletePlan('plan_mock001')

      expect(store.currentPlan).toBeNull()
    })
  })
})
