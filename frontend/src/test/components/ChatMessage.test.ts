import { describe, it, expect, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import type { MessageRecord } from '@/types/chat'

const mockRouterPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({ push: mockRouterPush }),
}))

const userMessage: MessageRecord = {
  id: 'msg_001',
  session_id: 'sess_001',
  role: 'user',
  content: '我想去云南大理玩5天',
  message_type: 'text',
  metadata: {},
  created_at: '2026-07-01T10:00:00Z',
}

const assistantMessage: MessageRecord = {
  id: 'msg_002',
  session_id: 'sess_001',
  role: 'assistant',
  content: '你好！大理是个绝美的目的地。让我为你规划5天行程！',
  message_type: 'text',
  metadata: { suggestions: ['可以开始了吗？'] },
  created_at: '2026-07-01T10:00:05Z',
}

const systemMessage: MessageRecord = {
  id: 'msg_003',
  session_id: 'sess_001',
  role: 'system',
  content: '正在规划中...',
  message_type: 'plan_progress',
  metadata: { step: 'planning', percent: 35 },
  created_at: '2026-07-01T10:00:10Z',
}

const progressMessage: MessageRecord = {
  id: 'msg_004',
  session_id: 'sess_001',
  role: 'system',
  content: '景点规划完成 (5天)',
  message_type: 'plan_progress',
  metadata: { step: 'planning', percent: 60 },
  created_at: '2026-07-01T10:00:15Z',
}

const planResultMessage: MessageRecord = {
  id: 'msg_005',
  session_id: 'sess_001',
  role: 'assistant',
  content: '大理5日游方案已为您规划完成！',
  message_type: 'plan_result',
  metadata: { plan_id: 'plan_mock001' },
  created_at: '2026-07-01T10:01:00Z',
}

const aProgressStub = {
  template: '<div class="ant-progress" :percent="percent"><slot /></div>',
  props: ['percent', 'show-info', 'stroke-color', 'size'],
}

const aButtonStub = {
  template: '<button class="ant-btn" @click="$emit(\'click\')"><slot /></button>',
}

describe('ChatMessage 组件渲染', () => {
  it('用户消息应正确渲染内容', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: userMessage },
      global: {
        stubs: { AppLogo: true, aProgress: aProgressStub, aButton: aButtonStub },
      },
    })

    expect(wrapper.text()).toContain('我想去云南大理玩5天')
  })

  it('AI 消息应正确渲染内容', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: assistantMessage },
      global: {
        stubs: { AppLogo: true, aProgress: aProgressStub, aButton: aButtonStub },
      },
    })

    expect(wrapper.text()).toContain('你好！大理是个绝美的目的地')
  })

  it('AI 消息应正确渲染 markdown 内容', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: assistantMessage },
      global: {
        stubs: { AppLogo: true, aProgress: aProgressStub, aButton: aButtonStub },
      },
    })

    // AI 消息走 Markdown 渲染, 内容以 cleaned 格式展示
    expect(wrapper.text()).toContain('大理是个绝美的目的地')
  })

  it('系统消息应正确渲染', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: systemMessage },
      global: {
        stubs: { AppLogo: true, aProgress: aProgressStub, aButton: aButtonStub },
      },
    })

    expect(wrapper.text()).toContain('正在规划中')
  })

  it('plan_progress 类型应渲染进度条', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: progressMessage },
      global: {
        stubs: { AppLogo: true, aProgress: aProgressStub, aButton: aButtonStub },
      },
    })

    expect(wrapper.text()).toContain('景点规划完成')
    expect(wrapper.find('.ant-progress').exists()).toBe(true)
  })

  it('plan_result 类型应渲染方案结果卡片和查看按钮', () => {
    const wrapper = mount(ChatMessage, {
      props: { message: planResultMessage },
      global: {
        stubs: { AppLogo: true, aProgress: aProgressStub, aButton: aButtonStub },
      },
    })

    expect(wrapper.text()).toContain('大理5日游方案已为您规划完成')
    expect(wrapper.find('.ant-btn').exists()).toBe(true)
    expect(wrapper.text()).toContain('查看完整方案')
  })

  it('plan_result 点击查看按钮应跳转至方案详情页', async () => {
    mockRouterPush.mockClear()

    const wrapper = mount(ChatMessage, {
      props: { message: planResultMessage },
      global: {
        stubs: { AppLogo: true, aProgress: aProgressStub, aButton: aButtonStub },
      },
    })

    await wrapper.find('.ant-btn').trigger('click')
    expect(mockRouterPush).toHaveBeenCalledWith('/plans/plan_mock001')
  })
})
