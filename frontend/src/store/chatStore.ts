// ============================================================
// 对话状态管理
// ============================================================

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { usePlanStore } from '@/store/planStore'
import type {
  ChatSession,
  ConversationPlanRunRecord,
  MessageRecord,
  SSEEventType,
  SSEStepStartData,
  SSEMessageData,
  SSEMessageDeltaData,
  SSEProgressData,
  SSEStepEndData,
  SSEErrorData,
  SSEDoneData,
} from '@/types/chat'
import {
  createSession as apiCreateSession,
  getSessions as apiGetSessions,
  deleteSession as apiDeleteSession,
  renameSession as apiRenameSession,
  togglePinSession as apiTogglePinSession,
  getMessages as apiGetMessages,
  getSessionPlans as apiGetSessionPlans,
} from '@/api/chat'
import {
  buildPlanResultMessage,
  COMPACT_PLAN_RESULT_FORMAT,
} from '@/utils/planResultMessage'

export type StreamPhase = 'idle' | 'chat' | 'planning'

export interface ParsedSSEEvent {
  event: SSEEventType
  data: Record<string, unknown>
}

const PLACEHOLDER_SESSION_TITLES = new Set(['新对话', '新的旅行规划'])
const PLAN_RESULT_REVEAL_INTERVAL_MS = 180

export function parseSSEFrames(buffer: string): {
  events: ParsedSSEEvent[]
  remainder: string
} {
  const events: ParsedSSEEvent[] = []
  let remainder = buffer

  while (true) {
    const separator = remainder.match(/\r?\n\r?\n/)
    if (!separator || separator.index === undefined) break

    const frame = remainder.slice(0, separator.index)
    remainder = remainder.slice(separator.index + separator[0].length)
    let event: SSEEventType | null = null
    const dataLines: string[] = []

    for (const line of frame.split(/\r?\n/)) {
      if (line.startsWith('event:')) {
        event = line.slice(6).trim() as SSEEventType
      } else if (line.startsWith('data:')) {
        dataLines.push(line.slice(5).trimStart())
      }
    }

    if (!event || dataLines.length === 0) continue
    try {
      events.push({ event, data: JSON.parse(dataLines.join('\n')) })
    } catch (error) {
      console.error('[chatStore] SSE parse error:', error)
    }
  }

  return { events, remainder }
}

export const useChatStore = defineStore('chat', () => {
  // ---- state ----

  const sessions = ref<ChatSession[]>([])
  const sessionsLoading = ref(false)
  const sessionsError = ref<string | null>(null)
  const currentSessionId = ref<string | null>(null)
  const messages = ref<MessageRecord[]>([])
  const isStreaming = ref(false)
  const streamPhase = ref<StreamPhase>('idle')
  const streamMessage = ref('')
  const retryCount = ref(0)
  const MAX_RETRIES = 10
  const abortController = ref<AbortController | null>(null)

  // ---- getters ----

  const currentSession = computed(() =>
    sessions.value.find((s) => s.id === currentSessionId.value) ?? null,
  )

  // ---- actions ----

  /**
   * 创建新会话
   */
  async function createSession(title?: string): Promise<ChatSession> {
    const result = await apiCreateSession(title ? { title } : {})
    const session: ChatSession = result.data!.data!
    sessions.value.unshift(session)
    currentSessionId.value = session.id
    messages.value = []
    // 清空方案状态（新会话无方案）
    const pStore = usePlanStore()
    pStore.currentPlan = null
    pStore.isGenerating = false
    return session
  }

  /**
   * 获取会话列表
   * 以后端数据为准
   */
  async function fetchSessions(): Promise<void> {
    sessionsLoading.value = true
    sessionsError.value = null
    try {
      const result = await apiGetSessions({ page_size: 50 })
      const list: ChatSession[] = result.data?.data?.list ?? []
      sessions.value = list
    } catch (error) {
      sessionsError.value = error instanceof Error ? error.message : '会话加载失败'
    } finally {
      sessionsLoading.value = false
    }
  }

  /**
   * 删除会话（优先本地删除，API 失败时静默）
   */
  async function deleteSession(id: string): Promise<void> {
    if (!id) return
    try {
      await apiDeleteSession(id)
    } catch {
      // API 失败（如后端无数据）时仍执行本地删除
    }
    sessions.value = sessions.value.filter((s) => s.id && s.id !== id)
    if (currentSessionId.value === id) {
      clearCurrentSession()
    }
  }

  /**
   * 重命名会话
   */
  async function renameSession(id: string, title: string): Promise<void> {
    if (!id || !title.trim()) return
    try {
      await apiRenameSession(id, title.trim())
      const session = sessions.value.find((s) => s.id === id)
      if (session) session.title = title.trim()
    } catch {
      // 静默
    }
  }

  /**
   * 置顶/取消置顶会话
   */
  async function togglePinSession(id: string, pinned: boolean): Promise<void> {
    if (!id) return
    try {
      await apiTogglePinSession(id, pinned)
      const session = sessions.value.find((s) => s.id === id)
      if (session) {
        session.pinned = pinned
        // 置顶的会话移到最前
        if (pinned) {
          sessions.value = [
            session,
            ...sessions.value.filter((s) => s.id !== id),
          ]
        }
      }
    } catch {
      // 静默
    }
  }

  /**
   * 加载历史消息（支持分页，新消息往前插入）
   * 失败时静默处理，不影响导航
   */
  async function loadHistory(sessionId: string, page?: number): Promise<void> {
    try {
      const result = await apiGetMessages(sessionId, { page, page_size: 50 })
      const list: MessageRecord[] = result.data?.data?.list ?? []
      const pStore = usePlanStore()
      for (let i = 0; i < list.length; i++) {
        const m = list[i]
        // 新方案：通过 message_type 识别方案结果消息（后端持久化）
        if (m.role === 'assistant' && m.message_type === 'plan_result' && m.metadata?.summary) {
          const summary = m.metadata.summary as Record<string, any>
          const isCompact = m.metadata.result_format === COMPACT_PLAN_RESULT_FORMAT
          list[i] = {
            ...m,
            content: isCompact && m.content.trim()
              ? m.content
              : buildPlanResultMessage(summary),
            message_type: 'plan_result',
            metadata: {
              ...m.metadata,
              summary,
              result_format: COMPACT_PLAN_RESULT_FORMAT,
            },
          } as any
          pStore.currentPlan = {
            ...(pStore.normalizeSSESummary(summary) as any),
            id: m.metadata.plan_id || '',
          }
          pStore.isGenerating = false
          pStore.persistCurrentPlan(sessionId)
          continue
        }
        // 兜底：plan_result 消息存在但缺少 summary（后端摘要查询失败），
        // 从 metadata.plan_id 走 API 获取方案详情
        if (m.role === 'assistant' && m.message_type === 'plan_result' && !m.metadata?.summary) {
          const planId = (m.metadata?.plan_id as string) || ''
          if (planId) {
            try {
              await pStore.fetchPlanDetail(planId, sessionId)
              // fetchPlanDetail 已设置 currentPlan，只需确保气泡内容可读
              list[i] = {
                ...m,
                content: pStore.currentPlan
                  ? `# 🗺️ ${(pStore.currentPlan as any).title || ''}\n\n方案已恢复。`
                  : m.content,
              } as any
            } catch {
              // 方案可能已被删除，静默
            }
          }
        }

        // 降级兼容：旧的 __PLAN__: 前缀消息（已废弃）
        if (m.role === 'assistant' && typeof m.content === 'string' && m.content.startsWith('__PLAN__:')) {
          const pipeIdx = m.content.indexOf('|')
          if (pipeIdx > 0) {
            try {
              const summary = JSON.parse(m.content.slice(pipeIdx + 1))
              list[i] = {
                ...m,
                content: buildPlanResultMessage(summary),
                message_type: 'plan_result' as any,
                metadata: {
                  summary,
                  result_format: COMPACT_PLAN_RESULT_FORMAT,
                },
              } as any
              pStore.currentPlan = {
                ...pStore.normalizeSSESummary(summary),
                id: '',
                content_blocks: summary.content_blocks || [],
              } as any
              pStore.isGenerating = false
              pStore.persistCurrentPlan(sessionId)
            } catch {
              // JSON 解析失败（数据损坏或旧截断数据），改用友好的回退文本
              const tripName = m.content.slice(8, pipeIdx) || '旅行方案'
              list[i] = {
                ...m,
                content: `# 🗺️ ${tripName}\n\n> 方案数据加载失败，请重新生成。`,
                message_type: 'plan_result' as any,
                metadata: {},
              } as any
            }
          }
        }
      }
      if (!page || page === 1) {
        messages.value = list
      } else {
        messages.value = [...list, ...messages.value]
      }
    } catch {
      // 后端无会话数据时静默处理，不影响导航
    }
  }

  function planResultMatchesRun(
    message: MessageRecord,
    run: ConversationPlanRunRecord,
  ): boolean {
    if (message.message_type !== 'plan_result') return false
    const messagePlanId = String(
      message.metadata?.plan_run_id || message.metadata?.plan_id || '',
    )
    if (messagePlanId) return messagePlanId === run.id

    const messageSummary = message.metadata?.summary as Record<string, any> | undefined
    if (!messageSummary) return false
    return String(messageSummary.destination || '') === String(run.summary.destination || run.destination || '')
      && Number(messageSummary.days || 0) === Number(run.summary.days || run.days || 0)
  }

  async function reconcilePlanResults(
    sessionId: string,
    fallbackRun?: ConversationPlanRunRecord,
  ): Promise<ConversationPlanRunRecord[]> {
    let runs: ConversationPlanRunRecord[]
    try {
      const result = await apiGetSessionPlans(sessionId)
      runs = result.data?.data ?? []
    } catch {
      runs = []
    }
    if (runs.length === 0 && fallbackRun) runs = [fallbackRun]
    if (runs.length === 0) return []

    const chronologicalRuns = [...runs].sort((left, right) => (
      Date.parse(left.created_at) - Date.parse(right.created_at)
    ))
    const restoredMessages: MessageRecord[] = []
    for (const run of chronologicalRuns) {
      if (messages.value.some(message => planResultMatchesRun(message, run))) continue
      const summary = {
        ...run.summary,
        destination: run.summary.destination || run.destination,
        days: run.summary.days || run.days,
      }
      restoredMessages.push({
        id: `restored_plan_${run.id}`,
        session_id: sessionId,
        role: 'assistant',
        content: buildPlanResultMessage(summary),
        message_type: 'plan_result',
        metadata: {
          plan_id: run.id,
          plan_run_id: run.id,
          summary,
          result_format: COMPACT_PLAN_RESULT_FORMAT,
        },
        created_at: run.created_at,
      })
    }

    if (restoredMessages.length > 0) {
      messages.value = [...messages.value, ...restoredMessages].sort((left, right) => {
        const timeDifference = Date.parse(left.created_at) - Date.parse(right.created_at)
        return Number.isNaN(timeDifference) ? 0 : timeDifference
      })
    }

    const latestRun = chronologicalRuns[chronologicalRuns.length - 1]
    if (latestRun?.summary && Object.keys(latestRun.summary).length > 0) {
      const pStore = usePlanStore()
      pStore.currentPlan = {
        ...(pStore.normalizeSSESummary(latestRun.summary) as any),
        id: latestRun.id,
      }
      pStore.isGenerating = false
      pStore.persistCurrentPlan(sessionId)
    }
    return chronologicalRuns
  }

  /**
   * 发送消息（SSE 流式接收）
   */
  async function sendMessage(content: string, images?: string[], isRetry = false): Promise<void> {
    if (!currentSessionId.value) {
      throw new Error('No active session')
    }

    // 防止重复发送
    if (isStreaming.value && !isRetry) {
      console.warn('[chatStore] Already streaming, message dropped:', content)
      return
    }
    isStreaming.value = true
    streamPhase.value = 'chat'
    streamMessage.value = '正在回复…'
    if (!isRetry) retryCount.value = 0

    // 1) 添加用户消息（乐观）——仅首次发送时添加，重试时不重复添加
    if (!isRetry) {
      const userMessage: MessageRecord = {
        id: `temp_${Date.now()}`,
        session_id: currentSessionId.value,
        role: 'user',
        content,
        message_type: 'text',
        metadata: images?.length ? { images } : {},
        created_at: new Date().toISOString(),
      }
      messages.value.push(userMessage)

      const session = sessions.value.find(s => s.id === currentSessionId.value)
      if (session && PLACEHOLDER_SESSION_TITLES.has((session.title || '').trim())) {
        const normalized = content.trim().replace(/\s+/g, ' ')
        session.title = normalized.length > 20
          ? normalized.slice(0, 20) + '…'
          : normalized
      }
    }

    // 2) 创建 AbortController
    const controller = new AbortController()
    abortController.value = controller

    try {
      // 3) 使用 fetch 发起 SSE 请求（POST 方式）
      const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api/v1'

      // 注入认证头
      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
        Accept: 'text/event-stream',
      }
      const token = localStorage.getItem('access_token')
      if (token) {
        headers['Authorization'] = `Bearer ${token}`
      } else {
        const sessionId = localStorage.getItem('anonymous_session_id')
        if (sessionId) {
          headers['X-Session-Id'] = sessionId
        }
      }

      const response = await fetch(
        `${API_BASE}/chat/sessions/${currentSessionId.value}/messages`,
        {
          method: 'POST',
          headers,
          body: JSON.stringify({ content, images: images || [] }),
          signal: controller.signal,
        },
      )

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`)
      }

      const reader = response.body?.getReader()
      if (!reader) {
        throw new Error('ReadableStream not supported')
      }

      // 4) 增量读取并处理 SSE
      const decoder = new TextDecoder()
      let sseBuffer = ''

      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        sseBuffer += decoder.decode(value, { stream: true })
        const parsed = parseSSEFrames(sseBuffer)
        sseBuffer = parsed.remainder
        for (const parsedEvent of parsed.events) {
          handleSSEEvent(parsedEvent.event, parsedEvent.data)
        }
      }

      sseBuffer += decoder.decode()
      const parsed = parseSSEFrames(sseBuffer)
      for (const parsedEvent of parsed.events) {
        handleSSEEvent(parsedEvent.event, parsedEvent.data)
      }
    } catch (error: unknown) {
      if ((error as Error).name === 'AbortError') {
        // 用户主动断开，不做处理
        return
      }
      retryCount.value++
      if (retryCount.value <= MAX_RETRIES) {
        console.warn(`[chatStore] SSE connection failed, retry ${retryCount.value}/${MAX_RETRIES}`)
        // 指数退避重试
        const delay = Math.min(1000 * Math.pow(2, retryCount.value), 30000)
        await new Promise((resolve) => setTimeout(resolve, delay))
        return sendMessage(content, images, true)  // isRetry=true, skip duplicate user message
      }
      throw error
    } finally {
      resetStreamState()
      abortController.value = null
    }
  }

  /**
   * 处理 SSE 事件分发
   */
  function handleSSEEvent(event: SSEEventType, data: Record<string, unknown>): void {
    switch (event) {
      case 'step_start': {
        const d = data as unknown as SSEStepStartData
        if (d.step === 'planning' || d.step === 'parallel_planning') {
          const ps = usePlanStore()
          ps.isGenerating = true
          ps.updateProgress({ percent: 0, message: d.label || '开始规划...', step: d.step })
          streamPhase.value = 'planning'
          streamMessage.value = d.label || '正在为您规划行程…'
        } else if (d.step === 'chat') {
          streamPhase.value = 'chat'
          streamMessage.value = '正在回复…'
        }
        break
      }

      case 'message': {
        const d = data as unknown as SSEMessageData
        const lastMessage = messages.value[messages.value.length - 1]
        if (
          lastMessage?.role === 'assistant'
          && lastMessage.message_type === 'text'
          && lastMessage.id.startsWith('stream_')
        ) {
          lastMessage.id = `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
          lastMessage.content = d.content
          lastMessage.message_type = d.message_type ?? 'text'
          lastMessage.metadata = d.suggestions
            ? { suggestions: d.suggestions }
            : undefined
        } else {
          messages.value.push({
            id: `msg_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`,
            session_id: currentSessionId.value ?? '',
            role: 'assistant',
            content: d.content,
            message_type: d.message_type ?? 'text',
            metadata: d.suggestions ? { suggestions: d.suggestions } : undefined,
            created_at: new Date().toISOString(),
          })
        }
        break
      }

      case 'progress': {
        const d = data as unknown as SSEProgressData
        const ps = usePlanStore()
        ps.updateProgress({ percent: d.percent, message: d.message })
        streamPhase.value = 'planning'
        streamMessage.value = d.message || '正在为您规划行程…'
        break
      }

      case 'step_end': {
        const d = data as unknown as SSEStepEndData
        if (d.step === 'chat' && streamPhase.value === 'chat') {
          streamPhase.value = 'idle'
          streamMessage.value = ''
        }
        break
      }

      case 'message_delta': {
        const d = data as unknown as SSEMessageDeltaData
        if (!d.content_delta) break
        const lastMessage = messages.value[messages.value.length - 1]
        if (
          lastMessage?.role === 'assistant'
          && lastMessage.message_type === 'text'
          && lastMessage.id.startsWith('stream_')
        ) {
          lastMessage.content += d.content_delta
        } else {
          messages.value.push({
            id: `stream_${Date.now()}`,
            session_id: currentSessionId.value ?? '',
            role: 'assistant',
            content: d.content_delta,
            message_type: 'text',
            created_at: new Date().toISOString(),
          })
        }
        break
      }

      case 'error': {
        const d = data as unknown as SSEErrorData
        messages.value.push({
          id: `error_${Date.now()}`,
          session_id: currentSessionId.value ?? '',
          role: 'system',
          content: d.message,
          message_type: 'text',
          created_at: new Date().toISOString(),
        })
        const planStore = usePlanStore()
        planStore.isGenerating = false
        streamPhase.value = 'idle'
        streamMessage.value = ''
        break
      }

      case 'done': {
        const d = data as Record<string, unknown>

        // 第一种 done：等待用户继续输入（非 READY 状态）
        if (d.status === 'waiting_input') {
          streamPhase.value = 'idle'
          streamMessage.value = ''
          break
        }

        if (d.status === 'idempotent_replay') {
          streamPhase.value = 'idle'
          streamMessage.value = ''
          break
        }

        // 第二种 done：方案生成完成
        const doneData = data as unknown as SSEDoneData
        const s = (doneData.summary || {}) as any
        const planText = doneData.result_message?.trim()
          || buildPlanResultMessage(s)
        const messageId = `done_${Date.now()}`
        const planLines = planText.split('\n').slice(0, 3)
        messages.value.push({
          id: messageId,
          session_id: currentSessionId.value ?? '',
          role: 'assistant',
          content: planLines[0] || planText,
          message_type: 'plan_result',
          metadata: {
            plan_id: doneData.plan_id,
            redirect_url: doneData.redirect_url,
            session_id: doneData.session_id,
            summary: doneData.summary,
            result_format: COMPACT_PLAN_RESULT_FORMAT,
          },
          created_at: new Date().toISOString(),
        })
        // 同步更新 planStore，让右侧方案面板显示可视化渲染
        const pStore = usePlanStore()
        if (doneData.summary) {
          const normalized = pStore.normalizeSSESummary(s)
          // 提取 SSE 中的 content_blocks（后端优化后提供）
          const extraData = data as Record<string, unknown>
          const contentBlocks = extraData.content_blocks || []
          pStore.currentPlan = {
            ...normalized,
            id: doneData.plan_id || `tmp_${Date.now()}`,
            _id: doneData.plan_id || `tmp_${Date.now()}`,
            content_blocks: contentBlocks,
          } as any
          pStore.isGenerating = false
          pStore.persistCurrentPlan(currentSessionId.value ?? undefined)
        }
        planLines.slice(1).forEach((line, index) => {
          setTimeout(() => {
            const message = messages.value.find(item => item.id === messageId)
            if (message) message.content += `\n${line}`
          }, (index + 1) * PLAN_RESULT_REVEAL_INTERVAL_MS)
        })
        pStore.isGenerating = false
        streamPhase.value = 'idle'
        streamMessage.value = ''
        break
      }

      default:
        console.warn('[chatStore] Unknown SSE event:', event, data)
    }
  }

  /**
   * 断开流式连接
   */
  function disconnectStream(): void {
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    resetStreamState()
  }

  function resetStreamState(): void {
    isStreaming.value = false
    streamPhase.value = 'idle'
    streamMessage.value = ''
    usePlanStore().isGenerating = false
  }

  /**
   * 清空当前会话状态
   */
  function clearCurrentSession(): void {
    currentSessionId.value = null
    messages.value = []
    resetStreamState()
    retryCount.value = 0
    if (abortController.value) {
      abortController.value.abort()
      abortController.value = null
    }
    // 切换/删除会话时同步清理方案状态
    const pStore = usePlanStore()
    pStore.clearCurrentPlan()
  }

  return {
    // state
    sessions,
    sessionsLoading,
    sessionsError,
    currentSessionId,
    messages,
    isStreaming,
    streamPhase,
    streamMessage,
    retryCount,
    MAX_RETRIES,
    abortController,
    // getters
    currentSession,
    // actions
    createSession,
    fetchSessions,
    deleteSession,
    renameSession,
    togglePinSession,
    loadHistory,
    reconcilePlanResults,
    sendMessage,
    handleSSEEvent,
    disconnectStream,
    clearCurrentSession,
  }
})
