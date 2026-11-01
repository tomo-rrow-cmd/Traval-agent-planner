<script setup lang="ts">
import { ref, onMounted, watch, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useChatStore } from '@/store/chatStore'
import { usePlanStore } from '@/store/planStore'
import {
  buildPlanResultMessage,
  COMPACT_PLAN_RESULT_FORMAT,
} from '@/utils/planResultMessage'
import type { ConversationPlanRunRecord } from '@/types/chat'
import type { PlanResponse } from '@/types/plan'
import { useUiStore } from '@/store/uiStore'
import ChatHistory from '@/components/chat/ChatHistory.vue'
import AppLogo from "@/components/brand/AppLogo.vue"
import ChatInput from '@/components/chat/ChatInput.vue'
import PlanPreview from '@/components/plan/PlanPreview.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import QuickSuggestions from '@/components/chat/QuickSuggestions.vue'
import FollowUpQuestions from '@/components/chat/FollowUpQuestions.vue'
import TagInputModal from '@/components/chat/TagInputModal.vue'
import CitySelector from '@/standalone/CitySelector.vue'

const route = useRoute()
const chatStore = useChatStore()
const planStore = usePlanStore()
const uiStore = useUiStore()

const sessionId = route.params.sessionId as string
const showPlanPanel = ref(false)
const splitRatio = ref(55)
const isLoadingHistory = ref(true)

/** 输入框内容（v-model 绑定） */
const inputContent = ref('')

/** 自定义标签弹窗 ref */
const tagInputModalRef = ref<InstanceType<typeof TagInputModal> | null>(null)

/** 快捷建议数据 */
const suggestions = ref([
  '大理', '成都', '杭州', '三亚', '丽江', '西安', '厦门', '重庆',
  '3天', '5天', '7天',
  '休闲放松', '美食之旅', '文化深度',
])

onMounted(async () => {
  await restoreSessionState(sessionId)

  if (uiStore.currentBreakpoint === 'lg') {
    showPlanPanel.value = true
  }

  // 测试数据：sessionId 为 "test-xxx" 时加载测试方案
  if (sessionId === 'test' || sessionId === 'test-chengdu' || sessionId === 'test-beijing' || sessionId === 'test-sanya' || sessionId === 'test-qingdao' || sessionId === 'test-wuhan' || sessionId === 'test-xian') {
    // 1) 加载测试方案数据（PlanPreview 面板 + PlanDetailPage）
    if (sessionId === 'test-beijing') {
      planStore.loadTestPlanBeijing()
    } else if (sessionId === 'test-chengdu') {
      planStore.loadTestPlanChengdu()
    } else if (sessionId === 'test-qingdao') {
      planStore.loadTestPlanQingdao()
    } else if (sessionId === 'test-wuhan') {
      planStore.loadTestPlanWuhan()
    } else if (sessionId === 'test-xian') {
      planStore.loadTestPlanXian()
    } else {
      planStore.loadTestPlan() // 默认：长沙7日深度游
    }
    showPlanPanel.value = true

    // 2) 注入 plan_result 消息到对话列表（聊天气泡渲染测试）
    const p = planStore.currentPlan
    if (p) {
      // 使用与新后端兼容的 rawSummary 格式生成摘要卡片
      const rawSummary = buildRawSummaryFromPlan(p as any)
      const resultMessage = buildPlanResultMessage(rawSummary)
      chatStore.messages.push({
        id: `test_plan_msg_${Date.now()}`,
        session_id: sessionId,
        role: 'assistant',
        content: resultMessage,
        message_type: 'plan_result' as any,
        metadata: {
          plan_id: p.id,
          summary: rawSummary,
          result_format: COMPACT_PLAN_RESULT_FORMAT,
        },
        created_at: new Date().toISOString(),
      } as any)
    }
  }
})

/** 将 PlanDetail 格式转为方案结果摘要所需的 rawSummary 格式 */
function buildRawSummaryFromPlan(p: Record<string, any>): Record<string, any> {
  return {
    destination: p.destination || '',
    origin: p.departure || '',
    days: p.days || 0,
    trip_name: p.title || '',
    total_budget: p.total_budget || 0,
    estimated_cost: p.estimated_cost || 0,
    pace: p.pace || '适中',
    trip_config: p.trip_config || { pace: p.pace || '适中', travelers: p.people_count || 1 },
    travelers: p.people_count || 1,
    weather_forecast: p.weather_forecast || [],
    daily_itinerary: (p.daily_itinerary || []).map((d: any) => ({
      day: d.day,
      date: d.date,
      date_label: d.date_label,
      weather_summary: d.weather_summary || '',
      day_cost: d.day_cost || 0,
      day_summary: d.day_summary || '',
      attractions: (d.activities || []).map((a: any) => ({
        name: a.title || '',
        reason: a.description || '',
        duration_hours: a.duration_minutes ? Math.round(a.duration_minutes / 60) : undefined,
        price: a.cost ?? a.price,
      })),
      meals: d.meals || [],
      hotel: d.accommodation ? {
        name: d.accommodation.hotel_name || '',
        price_per_night: d.accommodation.price || 0,
        total: d.accommodation.price ? d.accommodation.price * (p.days || 1) : 0,
        reason: '',
      } : undefined,
    })),
    meal_plan: p.meal_plan || [],
    big_traffic: p.big_traffic || {},
    traffic: p.traffic || {},
    hotel_plan: p.hotel_plan || {},
    budget: p.budget || {},
    attraction_details: p.attraction_details || [],
    food_details: p.food_details || [],
    packing_list: p.packing_list || [],
    tips: p.tips || [],
    avoid_list: p.avoid_list || [],
    souvenirs: p.souvenirs || p.souvenir_recommendations || [],
    overview: p.overview || { highlights: [] },
  }
}

function currentPlanFallbackRun(targetSessionId: string): ConversationPlanRunRecord | undefined {
  const plan = planStore.currentPlan as PlanResponse | null
  if (!plan) return undefined
  const session = chatStore.currentSession
  const planId = session?.plan_run_id || plan.id || plan._id || `local_${targetSessionId}`
  return {
    id: planId,
    destination: plan.destination || '',
    days: plan.days || 0,
    summary: buildRawSummaryFromPlan(plan as any),
    created_at: session?.updated_at || new Date().toISOString(),
  }
}

async function restoreSessionState(targetSessionId: string) {
  chatStore.currentSessionId = targetSessionId
  chatStore.messages = []
  planStore.currentPlan = null
  planStore.restoreCachedPlan(targetSessionId)
  isLoadingHistory.value = true
  try {
    await chatStore.loadHistory(targetSessionId)
    if (chatStore.sessions.length === 0) await chatStore.fetchSessions()

    const runs = await chatStore.reconcilePlanResults(
      targetSessionId,
      currentPlanFallbackRun(targetSessionId),
    )
    const planId = chatStore.currentSession?.plan_run_id
    if (!planStore.currentPlan && planId) {
      try {
        await planStore.fetchPlanDetail(planId, targetSessionId)
      } catch { /* 静默 */ }
      if (runs.length === 0) {
        await chatStore.reconcilePlanResults(
          targetSessionId,
          currentPlanFallbackRun(targetSessionId),
        )
      }
    }
  } finally {
    isLoadingHistory.value = false
  }
  showPlanPanel.value = !!planStore.currentPlan
    || (chatStore.currentSession?.plan_run_id != null)
    || uiStore.currentBreakpoint === 'lg'
}

watch(() => route.params.sessionId, async (newId) => {
  if (newId && typeof newId === 'string') {
    await restoreSessionState(newId)
  }
})

watch(() => planStore.isGenerating, (v) => {
  if (v) showPlanPanel.value = true
})

watch(() => planStore.currentPlan, (v) => {
  if (v) showPlanPanel.value = true
})

const lastAssistantMessage = computed(() => {
  return [...chatStore.messages].reverse().find(m => m.role === 'assistant')
})

const followUpSuggestions = computed(() => {
  const msg = lastAssistantMessage.value
  return (msg?.metadata?.suggestions as string[]) ?? []
})

/** 发送消息（含图片）后清空快捷建议 */
async function handleSend(content: string, images?: string[]) {
  suggestions.value = []
  try {
    await chatStore.sendMessage(content, images)
  } catch {
    uiStore.showError('发送失败，请重试')
  }
}

/** 点击快捷标签：追加到输入框，不直接发送 */
function handleAddTag(value: string) {
  if (inputContent.value) {
    inputContent.value += ` ${value}`
  } else {
    inputContent.value = value
  }
}

/** 自定义添加标签：弹出自定义弹窗 */
function handleAddCustom() {
  tagInputModalRef.value?.open()
}

/** 接收自定义标签弹窗确认：添加到快捷建议列表 */
function handleCustomTagConfirm(value: string) {
  if (!suggestions.value.includes(value) && suggestions.value.length < 20) {
    suggestions.value.push(value)
  }
}

/** 删除快捷标签 */
function handleRemoveTag(value: string) {
  const idx = suggestions.value.indexOf(value)
  if (idx !== -1) suggestions.value.splice(idx, 1)
}

/** 目的地选择：点击城市后自动填入并发送 */
function handleCitySelect(city: string) {
  chatStore.sendMessage(city)
}

function togglePlanPanel() {
  showPlanPanel.value = !showPlanPanel.value
}

const isDesktop = computed(() => uiStore.currentBreakpoint === 'lg')
</script>

<template>
  <div
    class="chat-session"
    :class="{ 'chat-session--split': showPlanPanel && isDesktop }"
  >
    <!-- 左栏：对话区 -->
    <div
      class="chat-session__chat"
      :style="showPlanPanel && isDesktop ? { width: `${splitRatio}%` } : {}"
    >
      <LoadingSpinner
        v-if="isLoadingHistory"
        tip="加载历史消息..."
      />
      <template v-else>
        <ChatHistory
          :messages="chatStore.messages"
          :loading="false"
        />
        <FollowUpQuestions
          v-if="followUpSuggestions.length > 1 && !chatStore.isStreaming"
          :question="followUpSuggestions[0]"
          :suggestions="followUpSuggestions.slice(1)"
          @answer="handleSend"
        />
        <QuickSuggestions
          v-if="chatStore.messages.length === 0 && !chatStore.isStreaming"
          :suggestions="suggestions"
          :max-tags="20"
          @add-tag="handleAddTag"
          @add-custom="handleAddCustom"
          @remove-tag="handleRemoveTag"
        />
      </template>
      <!-- 自定义标签弹窗 -->
      <TagInputModal
        ref="tagInputModalRef"
        :max-tags="20"
        :current-count="suggestions.length"
        @confirm="handleCustomTagConfirm"
      />
      <!-- 流式生成状态 -->
      <div
        v-if="chatStore.isStreaming && chatStore.streamMessage"
        class="chat-session__streaming"
      >
        <div class="chat-session__streaming-bar" />
        <div class="chat-session__streaming-content">
          <div class="chat-session__streaming-avatar">
            <AppLogo
              :size="16"
              style="color:white"
            />
          </div>
          <div class="chat-session__streaming-text">
            <span class="chat-session__streaming-label">旅行者</span>
            <span class="chat-session__streaming-message">{{ chatStore.streamMessage }}</span>
          </div>
          <div class="chat-session__streaming-dots">
            <span class="dot" /><span class="dot" /><span class="dot" />
          </div>
        </div>
      </div>
      <div class="chat-session__input-area">
        <CitySelector @select="handleCitySelect" />
        <ChatInput
          v-model="inputContent"
          :disabled="chatStore.isStreaming"
          :suggestions="[]"
          @send="handleSend"
        />
      </div>
    </div>

    <!-- 分屏切换按钮（移动端浮动） -->
    <button
      v-if="!isDesktop && (planStore.isGenerating || planStore.currentPlan)"
      class="chat-session__plan-toggle"
      @click="togglePlanPanel"
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
      >
        <rect
          x="3"
          y="4"
          width="18"
          height="18"
          rx="2"
          ry="2"
        />
        <line
          x1="16"
          y1="2"
          x2="16"
          y2="6"
        />
        <line
          x1="8"
          y1="2"
          x2="8"
          y2="6"
        />
      </svg>
      <span>{{ showPlanPanel ? '隐藏方案' : '查看方案' }}</span>
      <span
        v-if="planStore.isGenerating"
        class="chat-session__plan-dot"
      />
    </button>

    <!-- 展开按钮（桌面端，面板收起时显示） -->
    <button
      v-if="isDesktop && !showPlanPanel"
      class="chat-session__plan-expand"
      title="展开方案面板"
      @click="togglePlanPanel"
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
      >
        <path d="M9 18l6-6-6-6" />
      </svg>
    </button>

    <!-- 右栏：方案预览（带动画） -->
    <Transition name="plan-slide">
      <div
        v-if="showPlanPanel"
        key="plan-panel"
        class="chat-session__plan"
        :class="{ 'chat-session__plan--overlay': !isDesktop }"
        :style="isDesktop ? { width: `${100 - splitRatio}%` } : {}"
      >
        <PlanPreview @collapse="togglePlanPanel" />
        <button
          v-if="!isDesktop"
          class="chat-session__plan-close"
          @click="togglePlanPanel"
        >
          ✕
        </button>
      </div>
    </Transition>
  </div>
</template>

<style scoped>
.chat-session {
  display: flex;
  height: 100%;
  position: relative;
  overflow: hidden;
}

.chat-session__chat {
  display: flex;
  flex-direction: column;
  height: 100%;
  width: 100%;
  min-width: 0;
  transition: width var(--dur-slide) var(--ease-out-expo);
}

.chat-session--split .chat-session__chat {
  border-right: 1px solid var(--color-border);
}

/* 流式生成状态 */
.chat-session__streaming {
  position: relative;
  padding: var(--space-4) var(--space-6);
  background: var(--color-bg-card);
  border-top: 1px solid var(--color-border-light);
}

.chat-session__streaming-bar {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 2px;
  background: linear-gradient(90deg, var(--color-brand-300), var(--color-brand-500), var(--color-brand-300));
  background-size: 200% 100%;
  animation: shimmerBar 1.5s ease infinite;
}

@keyframes shimmerBar {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.chat-session__streaming-content {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.chat-session__streaming-avatar {
  width: 32px;
  height: 32px;
  background: var(--gradient-gold);
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 14px;
  color: white;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(232, 168, 124, 0.2);
  animation: pulseAvatar 2s ease infinite;
}

@keyframes pulseAvatar {
  0%, 100% { box-shadow: 0 4px 12px rgba(232, 168, 124, 0.2); }
  50% { box-shadow: 0 4px 20px rgba(232, 168, 124, 0.4); }
}

.chat-session__streaming-text {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.chat-session__streaming-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-brand-600);
}

.chat-session__streaming-message {
  font-size: 13px;
  color: var(--color-text-tertiary);
}

.chat-session__streaming-dots {
  display: flex;
  gap: 4px;
  margin-left: auto;
}

.chat-session__streaming-dots .dot {
  width: 6px;
  height: 6px;
  background: var(--color-brand-300);
  border-radius: 50%;
  animation: dotBounce 1.4s ease infinite;
}

.chat-session__streaming-dots .dot:nth-child(2) {
  animation-delay: 0.2s;
}
.chat-session__streaming-dots .dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* 方案面板 */
.chat-session__plan {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-width: 0;
  position: relative;
  animation: slideInRight var(--dur-slide) var(--ease-out-expo);
}

@keyframes slideInRight {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

.chat-session__plan--overlay {
  position: absolute;
  top: 0;
  right: 0;
  width: 85%;
  max-width: 400px;
  z-index: var(--z-drawer);
  box-shadow: var(--shadow-drawer);
}

.chat-session__plan-toggle {
  position: absolute;
  top: var(--space-4);
  right: var(--space-4);
  z-index: 5;
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-2) var(--space-3);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-pill);
  box-shadow: var(--shadow-float);
  color: var(--color-text-secondary);
  font-size: var(--text-small);
  cursor: pointer;
  transition: all var(--dur-fast);
}
.chat-session__plan-toggle:hover {
  border-color: var(--color-brand-300);
  color: var(--color-brand-600);
}

.chat-session__plan-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-brand-500);
  animation: pulse 1.5s ease infinite;
}

/* 展开按钮（桌面端，面板收起时） */
.chat-session__plan-expand {
  position: absolute;
  top: 50%;
  right: 0;
  transform: translateY(-50%);
  z-index: 5;
  width: 28px;
  height: 48px;
  border: 1px solid var(--color-border);
  border-right: none;
  background: var(--color-bg-card);
  border-radius: 8px 0 0 8px;
  color: var(--color-text-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-in-out);
  box-shadow: -2px 0 8px rgba(139, 115, 85, 0.06);
}
.chat-session__plan-expand:hover {
  color: var(--color-brand-500);
  border-color: var(--color-brand-300);
  background: var(--color-brand-50);
  box-shadow: -2px 0 12px rgba(232, 168, 124, 0.15);
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.chat-session__plan-close {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  width: 28px;
  height: 28px;
  border: none;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-full);
  font-size: 13px;
  color: var(--color-text-tertiary);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2;
}
.chat-session__plan-close:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

/* ===== 方案面板滑入/滑出动画 ===== */
.plan-slide-enter-active {
  transition: all 0.35s var(--ease-out-expo);
}
.plan-slide-leave-active {
  transition: all 0.25s var(--ease-in-out);
}
.plan-slide-enter-from {
  opacity: 0;
  transform: translateX(30px);
}
.plan-slide-leave-to {
  opacity: 0;
  transform: translateX(30px);
}

/* 覆盖式面板的动画 */
.chat-session__plan--overlay.plan-slide-enter-from,
.chat-session__plan--overlay.plan-slide-leave-to {
  transform: translateX(100%);
}

/* 输入区域 */
.chat-session__input-area {
  padding: var(--space-3) var(--space-6) var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  border-top: 1px solid var(--color-border-light);
}
</style>
