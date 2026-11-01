import type { ApiResponse, PaginatedData } from '@/types/api'
import type { ChatSession, MessageRecord, SSEEventType } from '@/types/chat'

export const mockSession: ChatSession = {
  id: 'sess_mock001',
  title: '云南大理5日游',
  status: 'active',
  message_count: 6,
  pinned: false,
  last_message_preview: '好的，我来为你规划大理5日游...',
  created_at: '2026-07-01T10:00:00Z',
  updated_at: '2026-07-01T10:05:00Z',
}

export const mockSessionList: PaginatedData<ChatSession> = {
  list: [
    mockSession,
    {
      id: 'sess_mock002',
      title: '北京周末游',
      status: 'active',
      message_count: 3,
      pinned: false,
      last_message_preview: '北京2天行程已经规划好了...',
      created_at: '2026-07-02T14:00:00Z',
      updated_at: '2026-07-02T14:10:00Z',
    },
  ],
  total: 2,
  page: 1,
  page_size: 20,
  total_pages: 1,
}

export const mockUserMessage: MessageRecord = {
  id: 'msg_mock_u1',
  session_id: 'sess_mock001',
  role: 'user',
  content: '我想去云南大理玩5天，喜欢自然风光和美食',
  message_type: 'text',
  metadata: {},
  created_at: '2026-07-01T10:00:00Z',
}

export const mockAssistantMessage: MessageRecord = {
  id: 'msg_mock_a1',
  session_id: 'sess_mock001',
  role: 'assistant',
  content: '好的！大理是个绝美的目的地。让我为你规划5天的行程，包含苍山洱海、古城美食和周边自然风光。',
  message_type: 'text',
  metadata: {
    suggestions: ['可以开始了吗？', '我想加入丽江行程', '预算控制在3000以内'],
  },
  created_at: '2026-07-01T10:00:05Z',
}

export const mockMessageList: PaginatedData<MessageRecord> = {
  list: [mockUserMessage, mockAssistantMessage],
  total: 2,
  page: 1,
  page_size: 50,
  total_pages: 1,
}

/**
 * 模拟后端 SSE 事件流
 * 模拟完整的 Agent 管线：聊天 → 规划 → 完成
 */
export const mockSSEEvents: { event: SSEEventType; data: Record<string, unknown> }[] = [
  // 阶段1: 聊天分析
  {
    event: 'step_start',
    data: { step: 'chat', label: '分析需求...' },
  },
  {
    event: 'message',
    data: {
      role: 'assistant',
      content: '大理是个绝美的目的地！5天时间可以深度体验苍山洱海、古城文化和周边自然风光。让我为你规划详细行程...',
      message_type: 'text',
      suggestions: [],
    },
  },
  {
    event: 'step_end',
    data: { step: 'chat' },
  },
  // 阶段2: 规划
  {
    event: 'step_start',
    data: { step: 'planning', label: '正在规划 大理 行程...' },
  },
  {
    event: 'progress',
    data: { percent: 10, message: '景点搜索中...' },
  },
  {
    event: 'progress',
    data: { percent: 35, message: '景点规划完成 (5天)' },
  },
  {
    event: 'progress',
    data: { percent: 60, message: '美食 + 住宿推荐完成' },
  },
  {
    event: 'progress',
    data: { percent: 90, message: '整合方案中...' },
  },
  {
    event: 'step_end',
    data: { step: 'planning' },
  },
  // 阶段3: 完成
  {
    event: 'done',
    data: {
      plan_id: 'plan_mock001',
      redirect_url: '/plans/plan_mock001',
      session_id: 'sess_mock001',
      summary: {
        destination: '云南大理',
        days: 5,
        daily_plan: [
          {
            day: 1,
            date: '2026-07-15',
            title: '古城初见',
            theme: '文化探索',
            activities: [
              {
                type: 'attraction',
                title: '大理古城',
                time_slot: '09:00-11:00',
                description: '漫步古城，感受白族文化',
                location: '大理市古城区',
                duration: 120,
                tips: '建议早起避开人流',
                price: 0,
                coordinates: { lat: 25.6800, lng: 100.1600 },
              },
              {
                type: 'food',
                title: '白族风味午餐',
                time_slot: '12:00-13:00',
                description: '品尝地道白族美食',
                location: '古城内',
                duration: 60,
                tips: '推荐酸辣鱼和乳扇',
                price: 80,
              },
            ],
          },
          {
            day: 2,
            date: '2026-07-16',
            title: '苍山洱海',
            theme: '自然风光',
            activities: [
              {
                type: 'attraction',
                title: '苍山国家地质公园',
                time_slot: '08:00-14:00',
                description: '乘坐缆车上苍山，俯瞰洱海全景',
                location: '苍山景区',
                duration: 360,
                tips: '带外套，山顶温度较低',
                price: 120,
                coordinates: { lat: 25.6900, lng: 100.1000 },
              },
            ],
          },
        ],
        meal_plan: [
          {
            day: 1,
            meals: [
              { type: 'lunch', restaurant: '白族风味餐厅', dishes: ['酸辣鱼', '乳扇'], avg_price: 80 },
              { type: 'dinner', restaurant: '古城小吃街', dishes: ['烤饵块', '凉鸡米线'], avg_price: 50 },
            ],
          },
        ],
        hotel_plan: {
          recommendations: [
            {
              name: '大理古城花筑奢酒店',
              star: 4,
              price_per_night: 450,
              total: 2250,
              highlights: '古城核心位置，白族庭院风格',
            },
          ],
        },
        traffic: {
          daily_plan: [],
          total_traffic_cost: 300,
        },
        budget: {
          total: 4500,
          breakdown: {
            accommodation: 2250,
            food: 800,
            attractions: 240,
            traffic: 300,
            shopping: 500,
            other: 410,
          },
          remaining: 500,
        },
        souvenirs: [
          { name: '白族扎染', description: '手工扎染方巾', price: 80, where_to_buy: '大理古城扎染坊' },
        ],
      },
    } as unknown as Record<string, unknown>,
  },
]

/**
 * 生成 SSE 字节流（模拟 fetch Response body）
 */
export function createSSEStream(
  events: { event: SSEEventType; data: Record<string, unknown> }[] = mockSSEEvents,
): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  let index = 0

  return new ReadableStream({
    async pull(controller) {
      if (index >= events.length) {
        controller.close()
        return
      }

      const { event, data } = events[index++]
      const lines = [
        `id: evt_${index}\n`,
        `event: ${event}\n`,
        `data: ${JSON.stringify(data)}\n\n`,
      ]

      for (const line of lines) {
        controller.enqueue(encoder.encode(line))
      }

      await new Promise((r) => setTimeout(r, 10))
    },
  })
}

export const mockCreateSessionResponse: ApiResponse<ChatSession> = {
  code: 0,
  message: '会话创建成功',
  data: mockSession,
}

export const mockSessionListResponse: ApiResponse<PaginatedData<ChatSession>> = {
  code: 0,
  message: '',
  data: mockSessionList,
}

export const mockMessageListResponse: ApiResponse<PaginatedData<MessageRecord>> = {
  code: 0,
  message: '',
  data: mockMessageList,
}