import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { parseSSEFrames, useChatStore } from '@/store/chatStore'
import { usePlanStore } from '@/store/planStore'

vi.mock('@/api/chat', () => ({
  createSession: vi.fn(),
  getSessions: vi.fn(),
  deleteSession: vi.fn(),
  getMessages: vi.fn(),
  getSessionPlans: vi.fn(),
  renameSession: vi.fn(),
  togglePinSession: vi.fn(),
}))

import {
  getMessages as apiGetMessages,
  getSessionPlans as apiGetSessionPlans,
  getSessions as apiGetSessions,
} from '@/api/chat'

describe('chatStore SSE 事件解析', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('handleSSEEvent — step_start', () => {
    it('chat step_start 只更新临时状态，不插入消息', () => {
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      store.handleSSEEvent('step_start', { step: 'chat', label: '分析需求...' })

      expect(store.messages).toHaveLength(0)
      expect(store.streamPhase).toBe('chat')
      expect(store.streamMessage).toBe('正在回复…')
    })
  })

  describe('fetchSessions', () => {
    it('失败时应暴露错误状态并结束加载', async () => {
      const store = useChatStore()
      vi.mocked(apiGetSessions).mockRejectedValue(new Error('network down'))

      await store.fetchSessions()

      expect(store.sessionsLoading).toBe(false)
      expect(store.sessionsError).toBe('network down')
    })

    it('成功时应以服务端列表替换本地列表', async () => {
      const store = useChatStore()
      store.sessions = [{ id: 'stale' } as any]
      vi.mocked(apiGetSessions).mockResolvedValue({
        data: { data: { list: [{ id: 'server' }] } },
      } as any)

      await store.fetchSessions()

      expect(store.sessions.map((session) => session.id)).toEqual(['server'])
      expect(store.sessionsError).toBeNull()
    })
  })

  describe('handleSSEEvent — message', () => {
    it('应创建新的 assistant 消息', () => {
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      store.handleSSEEvent('message', {
        role: 'assistant',
        content: '你好！大理是个美丽的地方',
        message_type: 'text',
        suggestions: [],
      })

      const aiMsg = store.messages.find((m) => m.role === 'assistant')
      expect(aiMsg).toBeDefined()
      expect(aiMsg?.content).toBe('你好！大理是个美丽的地方')
    })

    it('连续 message 事件应各自创建独立的 assistant 消息', () => {
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      store.handleSSEEvent('message', { role: 'assistant', content: '你好！', message_type: 'text', suggestions: [] })
      store.handleSSEEvent('message', { role: 'assistant', content: '大理是个好地方', message_type: 'text', suggestions: [] })

      // 后端每次发送完整内容，前端每次创建新消息（不再追加合并）
      const aiMsgs = store.messages.filter((m) => m.role === 'assistant')
      expect(aiMsgs).toHaveLength(2)
      expect(aiMsgs[0].content).toBe('你好！')
      expect(aiMsgs[1].content).toBe('大理是个好地方')
    })
  })

  describe('handleSSEEvent — progress', () => {
    it('应更新规划临时状态', () => {
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      store.handleSSEEvent('progress', { percent: 35, message: '景点规划完成 (5天)' })

      expect(store.messages).toHaveLength(0)
      expect(store.streamPhase).toBe('planning')
      expect(store.streamMessage).toBe('景点规划完成 (5天)')
    })

    it('连续 progress 应更新同一个临时状态', () => {
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      store.handleSSEEvent('progress', { percent: 35, message: '景点规划中...' })
      store.handleSSEEvent('progress', { percent: 90, message: '整合方案中...' })

      expect(store.messages).toHaveLength(0)
      expect(store.streamMessage).toBe('整合方案中...')
    })
  })

  describe('handleSSEEvent — step_end', () => {
    it('chat step_end 应清除临时状态', () => {
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      store.handleSSEEvent('step_start', { step: 'chat', label: '分析需求...' })
      store.handleSSEEvent('step_end', { step: 'chat' })

      expect(store.streamPhase).toBe('idle')
      expect(store.streamMessage).toBe('')
    })
  })

  describe('handleSSEEvent — error', () => {
    it('应插入错误消息', () => {
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      store.handleSSEEvent('error', { message: 'API 调用失败，请稍后重试' })

      const errorMsg = store.messages.find((m) => m.role === 'system' && m.content.includes('失败'))
      expect(errorMsg).toBeDefined()
    })
  })

  describe('handleSSEEvent — done', () => {
    it('应优先使用服务端摘要并保留完整 summary', () => {
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      const summary = {
        destination: '云南大理',
        days: 5,
        daily_plan: [],
        meal_plan: [],
        hotel_plan: { recommendations: [] },
        traffic: { daily_plan: [], total_traffic_cost: 300 },
        budget: { total: 4500, breakdown: {}, remaining: 500 },
        souvenirs: [],
      }

      store.handleSSEEvent('done', {
        plan_id: 'plan_mock001',
        redirect_url: '/plans/plan_mock001',
        session_id: 'sess_test',
        result_message: '✅ 服务端方案摘要',
        result_format: 'compact_v1',
        summary,
      })

      const doneMsg = store.messages.find((m) => m.message_type === 'plan_result')
      expect(doneMsg).toBeDefined()
      expect(doneMsg?.content).toBe('✅ 服务端方案摘要')
      expect(doneMsg?.metadata?.plan_id).toBe('plan_mock001')
      expect(doneMsg?.metadata?.summary).toEqual(summary)
      expect(doneMsg?.metadata?.result_format).toBe('compact_v1')
    })

    it('旧服务端缺少摘要字段时应本地生成精简消息', () => {
      vi.useFakeTimers()
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      store.handleSSEEvent('done', {
        plan_id: 'plan_legacy',
        redirect_url: '/plans/plan_legacy',
        session_id: 'sess_test',
        summary: {
          destination: '北京',
          origin: '武汉',
          days: 3,
          travelers: 1,
          budget: { actual_total: 1349, total_budget: 3000 },
          daily_itinerary: [{ day: 1, attractions: [{ name: '故宫' }] }],
        },
      })

      const doneMsg = store.messages.find((m) => m.message_type === 'plan_result')
      expect(doneMsg?.content).toBe('✅ 北京3日方案已生成')
      vi.advanceTimersByTime(360)
      expect(doneMsg?.content).toBe([
        '✅ 北京3日方案已生成',
        '武汉 → 北京 · 3天 · 1人',
        '预计 ¥1349 / 预算 ¥3000',
      ].join('\n'))
      expect(doneMsg?.content).not.toContain('故宫')
      vi.useRealTimers()
    })

    it('应将 message_delta 合并为单条流式消息并由最终消息收口', () => {
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      store.handleSSEEvent('message_delta', {
        role: 'assistant',
        content_delta: '正在',
        message_type: 'text',
        sequence: 1,
      })
      store.handleSSEEvent('message_delta', {
        role: 'assistant',
        content_delta: '规划',
        message_type: 'text',
        sequence: 2,
      })

      expect(store.messages).toHaveLength(1)
      expect(store.messages[0].content).toBe('正在规划')

      store.handleSSEEvent('message', {
        role: 'assistant',
        content: '正在规划您的行程',
        message_type: 'text',
      })

      expect(store.messages).toHaveLength(1)
      expect(store.messages[0].content).toBe('正在规划您的行程')
      expect(store.messages[0].id).not.toMatch(/^stream_/)
    })
  })

  describe('loadHistory — plan_result', () => {
    it('应将旧版完整 Markdown 自动缩短为摘要', async () => {
      const store = useChatStore()
      const summary = {
        destination: '北京',
        origin: '武汉',
        days: 3,
        travelers: 1,
        budget: { actual_total: 1349, total_budget: 3000 },
        daily_itinerary: [{ day: 1, attractions: [{ name: '故宫' }] }],
      }
      vi.mocked(apiGetMessages).mockResolvedValue({
        data: { data: { list: [{
          id: 'legacy_plan',
          session_id: 'sess_test',
          role: 'assistant',
          content: '# 北京3日之旅\n## 第1天\n### 故宫',
          message_type: 'plan_result',
          metadata: { plan_id: 'plan_legacy', summary },
          created_at: '2026-07-17T00:00:00Z',
        }] } },
      } as any)

      await store.loadHistory('sess_test')

      expect(store.messages[0].content).toBe([
        '✅ 北京3日方案已生成',
        '武汉 → 北京 · 3天 · 1人',
        '预计 ¥1349 / 预算 ¥3000',
      ].join('\n'))
      expect(store.messages[0].metadata?.result_format).toBe('compact_v1')
    })

    it('应保留新版 compact_v1 服务端消息', async () => {
      vi.mocked(apiGetMessages).mockResolvedValue({
        data: { data: { list: [{
          id: 'compact_plan',
          session_id: 'sess_test',
          role: 'assistant',
          content: '✅ 服务端已生成摘要',
          message_type: 'plan_result',
          metadata: {
            plan_id: 'plan_compact',
            result_format: 'compact_v1',
            summary: { destination: '北京', days: 3 },
          },
          created_at: '2026-07-17T00:00:00Z',
        }] } },
      } as any)
      const store = useChatStore()

      await store.loadHistory('sess_test')

      expect(store.messages[0].content).toBe('✅ 服务端已生成摘要')
    })
  })

  describe('reconcilePlanResults', () => {
    it('应补齐全部缺失方案并以最新方案恢复右侧面板', async () => {
      const store = useChatStore()
      vi.mocked(apiGetSessionPlans).mockResolvedValue({
        data: { data: [
          {
            id: 'run-new', destination: '杭州', days: 2,
            summary: { destination: '杭州', days: 2 },
            created_at: '2026-07-17T10:00:00Z',
          },
          {
            id: 'run-old', destination: '北京', days: 3,
            summary: { destination: '北京', days: 3 },
            created_at: '2026-07-17T08:00:00Z',
          },
        ] },
      } as any)

      const runs = await store.reconcilePlanResults('sess_test')

      expect(runs.map(run => run.id)).toEqual(['run-old', 'run-new'])
      expect(store.messages.map(message => message.metadata?.plan_id)).toEqual([
        'run-old',
        'run-new',
      ])
      expect(store.messages[0].content).toBe('✅ 北京3日方案已生成\n北京 · 3天')
      expect(store.messages[1].content).toBe('✅ 杭州2日方案已生成\n杭州 · 2天')
      expect(usePlanStore().currentPlan?.id).toBe('run-new')
    })

    it('已有结果只补缺失方案且重复恢复不新增消息', async () => {
      const store = useChatStore()
      store.messages = [{
        id: 'existing-result',
        session_id: 'sess_test',
        role: 'assistant',
        content: '✅ 北京3日方案已生成',
        message_type: 'plan_result',
        metadata: { plan_run_id: 'run-old', summary: { destination: '北京', days: 3 } },
        created_at: '2026-07-17T08:00:00Z',
      }]
      vi.mocked(apiGetSessionPlans).mockResolvedValue({
        data: { data: [
          {
            id: 'run-old', destination: '北京', days: 3,
            summary: { destination: '北京', days: 3 },
            created_at: '2026-07-17T08:00:00Z',
          },
          {
            id: 'run-new', destination: '杭州', days: 2,
            summary: { destination: '杭州', days: 2 },
            created_at: '2026-07-17T10:00:00Z',
          },
        ] },
      } as any)

      await store.reconcilePlanResults('sess_test')
      await store.reconcilePlanResults('sess_test')

      expect(store.messages).toHaveLength(2)
      expect(store.messages.filter(message => message.metadata?.plan_id === 'run-new')).toHaveLength(1)
    })

    it('方案运行接口失败时应使用缓存方案兜底', async () => {
      const store = useChatStore()
      vi.mocked(apiGetSessionPlans).mockRejectedValue(new Error('network down'))

      await store.reconcilePlanResults('sess_test', {
        id: 'run-cached',
        destination: '北京',
        days: 3,
        summary: {
          destination: '北京', origin: '武汉', days: 3, travelers: 1,
          budget: { total_budget: 3000 },
        },
        created_at: '2026-07-17T08:00:00Z',
      })

      expect(store.messages).toHaveLength(1)
      expect(store.messages[0].content).toContain('武汉 → 北京 · 3天 · 1人')
      expect(store.messages[0].metadata?.result_format).toBe('compact_v1')
    })
  })

  describe('完整 Agent 管线模拟', () => {
    it('按顺序处理 6 种事件应得到完整的消息列表', () => {
      const store = useChatStore()
      store.currentSessionId = 'sess_test'

      store.handleSSEEvent('step_start', { step: 'chat', label: '分析需求...' })
      store.handleSSEEvent('message', { role: 'assistant', content: '大理5日游规划中', message_type: 'text', suggestions: [] })
      store.handleSSEEvent('step_end', { step: 'chat' })
      store.handleSSEEvent('step_start', { step: 'planning', label: '正在规划行程...' })
      store.handleSSEEvent('progress', { percent: 35, message: '景点规划完成' })
      store.handleSSEEvent('progress', { percent: 90, message: '整合方案中' })
      store.handleSSEEvent('step_end', { step: 'planning' })
      store.handleSSEEvent('done', {
        plan_id: 'plan_001',
        redirect_url: '/plans/plan_001',
        session_id: 'sess_test',
        summary: { destination: '云南大理', days: 5 },
      })

      expect(store.messages).toHaveLength(2)

      const assistantMsgs = store.messages.filter((m) => m.role === 'assistant')
      expect(assistantMsgs.length).toBeGreaterThanOrEqual(1)

      const planResult = store.messages.find((m) => m.message_type === 'plan_result')
      expect(planResult).toBeDefined()
      expect(planResult?.metadata?.plan_id).toBe('plan_001')
      expect(store.messages.some((message) => message.message_type === 'plan_progress')).toBe(false)
    })
  })

  describe('parseSSEFrames', () => {
    it('应保留被拆开的事件并在后续数据到达时解析', () => {
      const first = parseSSEFrames('event: step_start\ndata: {"step":"chat"')
      expect(first.events).toHaveLength(0)

      const second = parseSSEFrames(first.remainder + '}\n\nevent: done\ndata: {"status":"waiting_input"}\n\n')
      expect(second.events).toEqual([
        { event: 'step_start', data: { step: 'chat' } },
        { event: 'done', data: { status: 'waiting_input' } },
      ])
      expect(second.remainder).toBe('')
    })

    it('应忽略 keepalive 注释帧', () => {
      const parsed = parseSSEFrames(': keepalive\n\nevent: message\ndata: {"content":"你好"}\n\n')

      expect(parsed.events).toEqual([
        { event: 'message', data: { content: '你好' } },
      ])
    })
  })
})
