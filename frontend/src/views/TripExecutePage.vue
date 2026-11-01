<script setup lang="ts">
/**
 * V2.0 TripExecutePage — 行程执行主页面
 *
 * 显示当日行程时间线、签到按钮、进度追踪、调整建议
 */
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useTripStore } from '@/store/tripStore'
import { usePlanStore } from '@/store/planStore'
import { useTravelogueStore } from '@/store/travelogueStore'
import { useUiStore } from '@/store/uiStore'
import TripTimeline from '@/components/trip/TripTimeline.vue'
import AdjustmentBanner from '@/components/trip/AdjustmentBanner.vue'
import ProgressBar from '@/components/trip/ProgressBar.vue'
import ExpenseSummary from '@/components/trip/ExpenseSummary.vue'

const route = useRoute()
const router = useRouter()
const store = useTripStore()
const planStore = usePlanStore()
const travelogueStore = useTravelogueStore()
const uiStore = useUiStore()

const tripId = computed(() => route.params.tripId as string)
const showCheckinForm = ref(false)
const checkinTarget = ref<{ type: string; name: string } | null>(null)
const checkinRating = ref(0)
const checkinNote = ref('')
const checkinCost = ref<number | null>(null)
const isSubmitting = ref(false)
const checkinError = ref('')
const showCompleteConfirm = ref(false)
const showTraveloguePrompt = ref(false)

// 天级导航：当前查看的天数（默认 = 行程当前天，可手动切换）
const currentViewDay = ref(1)

// 方案总天数
const totalDays = computed(() => planStore.currentPlan?.daily_itinerary?.length || 1)
const executionDay = computed(() => store.activeTrip?.current_day ?? 1)
const canAdvanceDay = computed(() => (
  store.isTripActive
  && currentViewDay.value === executionDay.value
  && executionDay.value < totalDays.value
))
const showNextDayReminder = computed(() => Boolean(
  store.reminder?.reminder_text
  && currentViewDay.value === executionDay.value
  && executionDay.value < totalDays.value
))
const showReminderLoading = computed(() => (
  store.reminderLoading
  && currentViewDay.value === executionDay.value
  && executionDay.value < totalDays.value
))
const currentTripTravelogue = computed(() => (
  travelogueStore.current?.trip_id === tripId.value
    ? travelogueStore.current
    : null
))

// 当前查看天数的签到记录（按 source_day 过滤）
const viewDayCheckins = computed(() =>
  store.checkins.filter(c => c.source_day === currentViewDay.value)
)

// 当前查看天数的行程摘要（从 daily_itinerary 取 day_summary）
const viewDaySummary = computed(() => {
  const day = planStore.currentPlan?.daily_itinerary?.find((d: any) => d.day === currentViewDay.value)
  return day?.day_summary || ''
})

// 切换天数
function goToDay(day: number) {
  if (day < 1 || day > totalDays.value) return
  currentViewDay.value = day
}
function prevDay() { goToDay(currentViewDay.value - 1) }
function nextDay() { goToDay(currentViewDay.value + 1) }

// 签到表单重置
function resetCheckinForm() {
  checkinRating.value = 0
  checkinNote.value = ''
  checkinCost.value = null
  checkinError.value = ''
}

// 前端 ActivityType → 后端 poi_type 映射
const TYPE_MAP: Record<string, string> = {
  food: 'restaurant',
  attraction: 'attraction',
  shopping: 'other',
  rest: 'other',
  entertainment: 'other',
  accommodation: 'hotel',
  transport: 'other',
}

/** 当日行程的时间线插槽（从方案 daily_itinerary 提取，跟随 currentViewDay） */
const planSlots = computed(() => {
  const plan = planStore.currentPlan
  const day = plan?.daily_itinerary?.find((d: any) => d.day === currentViewDay.value)
  if (!day) return []
  const slots: Array<{ time: string; type: string; name: string }> = []
  const addedNames = new Set<string>()

  // 活动节点
  for (const act of day.activities || []) {
    const name = act.title || (act as any).name || ''
    if (!name || addedNames.has(name)) continue
    addedNames.add(name)
    slots.push({
      time: (
        act.time_slot
        || (act as any).time
        || (act as any).start_time
        || (act as any).time_range
        || ''
      ).split('-')[0]?.trim(),
      type: TYPE_MAP[act.type] || act.type || 'attraction',
      name,
    })
  }

  // 用餐节点
  const meals = (day as any).meals ?? []
  for (const m of meals) {
    const name = m.restaurant || '用餐'
    if (addedNames.has(name)) continue
    addedNames.add(name)
    slots.push({
      time: m.time || m.time_slot || m.meal_time || '',
      type: 'restaurant',
      name,
    })
  }

  if (day.accommodation) {
    const hotel = day.accommodation
    slots.push({
      time: hotel.check_in || '住宿',
      type: 'hotel',
      name: `入住 ${hotel.hotel_name}`,
    })
  }

  // 按时间排序
  slots.sort((a, b) => a.time.localeCompare(b.time))

  return slots
})

onMounted(async () => {
  // 测试模式：tripId 为 test/test-over/test-complete/test-empty 时加载 mock 数据
  const testScenarios: Record<string, 'normal' | 'over-budget' | 'completed' | 'empty'> = {
    test: 'normal',
    'test-over': 'over-budget',
    'test-complete': 'completed',
    'test-empty': 'empty',
  }
  const scenario = testScenarios[tripId.value]
  if (scenario) {
    store.loadTestTrip(scenario)
    // 不同场景加载不同方案数据，让每天内容明显不同
    if (!planStore.currentPlan?.daily_itinerary?.length) {
      if (tripId.value === 'test-complete') {
        planStore.loadTestPlanBeijing()
      } else if (tripId.value === 'test-over') {
        planStore.loadTestPlanChengdu()
      } else {
        planStore.loadTestPlan()
      }
    }
    currentViewDay.value = store.activeTrip?.current_day || 1
    return
  }

  await store.fetchTrip(tripId.value)
  currentViewDay.value = store.activeTrip?.current_day || 1
  const planId = store.activeTrip?.plan_id
  const hasPlanData = planStore.currentPlan?.id === planId
      && planStore.currentPlan?.daily_itinerary?.length
  if (planId && !hasPlanData) {
    await planStore.fetchPlanDetail(planId).catch(() => {})
  }
  const dataRequests = [
    store.fetchProgress(tripId.value),
    store.fetchCheckins(),
    store.fetchExpenses(),
    store.fetchAdjustments(),
  ]
  if (executionDay.value < totalDays.value) {
    dataRequests.push(store.fetchReminder().catch(() => {}))
  } else {
    store.clearReminder()
  }
  await Promise.all(dataRequests)
  if (store.activeTrip?.status === 'completed') {
    await travelogueStore.fetchByTrip(tripId.value).catch(() => {})
  }
})

function openCheckin(type: string, name: string) {
  checkinTarget.value = { type, name }
  resetCheckinForm()
  showCheckinForm.value = true
}

async function handleCheckinSubmit() {
  if (isSubmitting.value || !checkinTarget.value) return
  isSubmitting.value = true
  checkinError.value = ''
  try {
    await store.doCheckin({
      poi_type: checkinTarget.value.type,
      poi_name: checkinTarget.value.name,
      source_day: currentViewDay.value,
      actual_at: new Date().toISOString(),
      rating: checkinRating.value || undefined,
      note: checkinNote.value || undefined,
      actual_cost: checkinCost.value || undefined,
    })
    showCheckinForm.value = false
    checkinTarget.value = null
    // 刷新数据
    await Promise.all([
      store.fetchTrip(tripId.value),
      store.fetchProgress(),
      store.fetchCheckins(),
      store.fetchExpenses(),
    ])
    // 检测是否需要调整建议
    store.doDetectAnomalies('time_drift', {}).catch(() => {})
  } catch (error: any) {
    checkinError.value = (
      error?.response?.data?.detail
      || error?.response?.data?.message
      || error?.message
      || '签到失败，请重试'
    )
  } finally {
    isSubmitting.value = false
  }
}

async function handlePause() {
  await store.pauseTrip()
}

async function handleResume() {
  await store.resumeTrip()
}

async function handleComplete() {
  showCompleteConfirm.value = true
}

async function confirmComplete() {
  showCompleteConfirm.value = false
  await store.completeTrip()
  await travelogueStore.fetchByTrip(tripId.value).catch(() => {})
  // 完成旅行后弹出询问是否写游记
  showTraveloguePrompt.value = true
}

async function goToTravelogue() {
  showTraveloguePrompt.value = false
  await handleGenerateTravelogue()
}

async function handleGenerateTravelogue() {
  const trip = store.activeTrip
  if (!trip?.id || travelogueStore.isGenerating) return
  if (currentTripTravelogue.value?.id) {
    router.push(`/travelogues/${currentTripTravelogue.value.id}`)
    return
  }
  try {
    await travelogueStore.generate(trip.id, 'diary')
    if (travelogueStore.current?.id) {
      uiStore.showSuccess('游记生成成功！')
      router.push(`/travelogues/${travelogueStore.current.id}?edit=true`)
    }
  } catch (error: any) {
    uiStore.showError(error?.response?.data?.detail || error?.message || '游记生成失败')
  }
}

async function handleAdvanceDay() {
  if (!store.activeTrip || !canAdvanceDay.value) return
  try {
    await store.doAdvanceDay()
    currentViewDay.value = store.activeTrip?.current_day || 1
    const refreshRequests = [
      store.fetchProgress(),
      store.fetchCheckins(),
    ]
    if (executionDay.value < totalDays.value) {
      refreshRequests.push(store.fetchReminder().catch(() => {}))
    } else {
      store.clearReminder()
    }
    await Promise.all(refreshRequests)
  } catch (error: any) {
    uiStore.showError(error?.response?.data?.detail || error?.message || '推进天数失败')
  }
}

function backToPlans() {
  router.push('/plans')
}
</script>

<template>
  <div class="trip-execute-page">
    <!-- Header -->
    <div class="trip-header">
      <button
        class="btn-back"
        @click="backToPlans"
      >
        ← 返回
      </button>
      <div class="header-info">
        <h1>行程执行中</h1>
        <span class="day-badge">第 {{ currentViewDay }} / {{ totalDays }} 天</span>
        <span :class="['status-badge', store.activeTrip?.status]">
          {{ store.activeTrip?.status === 'active' ? '进行中' :
            store.activeTrip?.status === 'paused' ? '已暂停' :
            store.activeTrip?.status === 'completed' ? '已完成' : '' }}
        </span>
      </div>
      <div class="header-actions">
        <button
          v-if="store.isTripActive"
          class="btn btn-outline"
          @click="handlePause"
        >
          暂停
        </button>
        <button
          v-if="store.isTripPaused"
          class="btn btn-primary"
          @click="handleResume"
        >
          继续
        </button>
        <button
          v-if="store.isTripActive || store.isTripPaused"
          class="btn btn-success"
          @click="handleComplete"
        >
          完成旅行
        </button>
        <button
          v-if="store.activeTrip?.status === 'completed'"
          class="btn btn-primary"
          :disabled="travelogueStore.isGenerating"
          @click="handleGenerateTravelogue"
        >
          {{ travelogueStore.isGenerating
            ? 'AI 正在生成整趟游记…'
            : currentTripTravelogue ? '查看游记' : '生成整趟游记' }}
        </button>
      </div>
    </div>

    <!-- 天级导航 -->
    <div
      v-if="totalDays > 1"
      class="day-navigator"
    >
      <button
        class="day-arrow"
        :disabled="currentViewDay <= 1"
        @click="prevDay"
      >
        ‹
      </button>
      <div class="day-chips">
        <button
          v-for="d in totalDays"
          :key="d"
          :class="['day-chip', {
            active: d === currentViewDay,
            current: d === (store.activeTrip?.current_day ?? 1),
          }]"
          @click="goToDay(d)"
        >
          <span class="day-num">第{{ d }}天</span>
          <span
            v-if="d === (store.activeTrip?.current_day ?? 1)"
            class="day-badge-current"
          >进行中</span>
        </button>
      </div>
      <button
        class="day-arrow"
        :disabled="currentViewDay >= totalDays"
        @click="nextDay"
      >
        ›
      </button>
      <button
        v-if="canAdvanceDay"
        class="btn btn-advance"
        @click="handleAdvanceDay"
      >
        完成第 {{ executionDay }} 天 →
      </button>
    </div>

    <!-- 当天行程摘要 -->
    <div
      v-if="viewDaySummary"
      class="day-summary-bar"
    >
      <span class="day-summary-icon">📋</span>
      <span class="day-summary-text">{{ viewDaySummary }}</span>
    </div>

    <!-- Progress -->
    <ProgressBar
      :percent="store.progressPct"
      :checked="store.progress?.checked_in ?? 0"
      :total="store.progress?.total_pois ?? 0"
    />

    <div class="trip-body">
      <!-- Left: Timeline -->
      <div
        v-if="showReminderLoading || showNextDayReminder"
        class="reminder-banner"
      >
        <div
          v-if="showReminderLoading"
          class="reminder-loading"
        >
          <span class="reminder-loading-dot" />
          正在准备第 {{ executionDay + 1 }} 天提醒…
        </div>
        <div
          v-else
          class="reminder-text"
        >
          {{ store.reminder.reminder_text }}
        </div>
        <div
          v-if="!showReminderLoading && store.reminder?.packing_hint"
          class="reminder-hint"
        >
          🎒 {{ store.reminder.packing_hint }}
        </div>
      </div>
      <div class="timeline-section">
        <TripTimeline
          :checkins="viewDayCheckins"
          :current-day="currentViewDay"
          :plan-slots="planSlots"
          @checkin="openCheckin"
        />
      </div>

      <!-- Right: Info Panel -->
      <div class="info-panel">
        <ExpenseSummary
          :budget-total="store.progress?.budget_total ?? 0"
          :budget-spent="store.progress?.budget_spent ?? 0"
          :budget-remain="store.progress?.budget_remain ?? 0"
        />

        <AdjustmentBanner
          :adjustments="store.adjustments.filter(a => a.status === 'pending')"
          @accept="(id) => store.doAcceptAdjustment(id)"
          @reject="(id) => store.doRejectAdjustment(id)"
        />

        <div class="quick-stats">
          <div class="stat-item">
            <span class="stat-label">已打卡</span>
            <span class="stat-value">{{ store.progress?.checked_in ?? 0 }}/{{ store.progress?.total_pois ?? 0 }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">时间偏差</span>
            <span class="stat-value">{{ store.progress?.time_delta_total_min ?? 0 }}min</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">剩余预算</span>
            <span class="stat-value">¥{{ (store.progress?.budget_remain ?? 0).toFixed(0) }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- Checkin Modal -->
    <Teleport to="body">
      <div
        v-if="showCheckinForm"
        class="modal-overlay"
        @click.self="showCheckinForm = false"
      >
        <div class="checkin-modal">
          <h2>📍 签到</h2>
          <p class="checkin-poi">
            {{ checkinTarget?.name }}
          </p>
          <form @submit.prevent="handleCheckinSubmit">
            <p
              v-if="checkinError"
              class="checkin-error"
            >
              {{ checkinError }}
            </p>
            <div class="form-group">
              <label>评分</label>
              <div class="star-rating">
                <button
                  v-for="i in 5"
                  :key="i"
                  type="button"
                  :class="{ active: i <= checkinRating }"
                  @click="checkinRating = i"
                >
                  ★
                </button>
              </div>
            </div>
            <div class="form-group">
              <label>备注</label>
              <textarea
                v-model="checkinNote"
                rows="3"
                placeholder="记录此刻的感受..."
              />
            </div>
            <div class="form-group">
              <label>实际花费 ¥</label>
              <input
                v-model.number="checkinCost"
                type="number"
                step="0.01"
                placeholder="0.00"
              >
            </div>
            <div class="form-actions">
              <button
                type="button"
                class="btn btn-outline"
                @click="showCheckinForm = false"
              >
                取消
              </button>
              <button
                type="submit"
                class="btn btn-primary"
                :disabled="isSubmitting"
              >
                {{ isSubmitting ? '签到中...' : '确认签到 ✓' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>

    <!-- Complete Confirm Dialog -->
    <Teleport to="body">
      <div
        v-if="showCompleteConfirm"
        class="modal-overlay"
        @click.self="showCompleteConfirm = false"
      >
        <div class="confirm-dialog">
          <div class="confirm-icon">
            🎉
          </div>
          <h2>完成旅行</h2>
          <p>确定要结束这次旅行吗？<br>完成后可以生成一篇游记记录美好时光。</p>
          <div class="form-actions">
            <button
              type="button"
              class="btn btn-outline"
              @click="showCompleteConfirm = false"
            >
              再玩会儿
            </button>
            <button
              type="button"
              class="btn btn-success"
              @click="confirmComplete"
            >
              确定完成
            </button>
          </div>
        </div>
      </div>
    </Teleport>

    <!-- Travelogue Prompt Dialog -->
    <Teleport to="body">
      <div
        v-if="showTraveloguePrompt"
        class="modal-overlay"
        @click.self="showTraveloguePrompt = false"
      >
        <div class="confirm-dialog">
          <div class="confirm-icon">
            📝
          </div>
          <h2>写一篇游记？</h2>
          <p>旅行已经完成啦！<br>让 AI 根据原方案和实际记录，按天生成一篇整趟旅行游记初稿。</p>
          <div class="form-actions">
            <button
              type="button"
              class="btn btn-outline"
              @click="showTraveloguePrompt = false"
            >
              不了，谢谢
            </button>
            <button
              type="button"
              class="btn btn-primary"
              :disabled="travelogueStore.isGenerating"
              @click="goToTravelogue"
            >
              {{ travelogueStore.isGenerating ? 'AI 正在按天生成初稿…' : '好的，生成整趟游记' }}
            </button>
          </div>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.trip-execute-page {
  max-width: 1100px;
  margin: 0 auto;
  padding: 20px;
  color: var(--color-text-primary);
}

.trip-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 20px;
}

.btn-back {
  background: none;
  border: none;
  color: var(--color-text-secondary);
  cursor: pointer;
  font-size: 14px;
}

.header-info {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 12px;
}

.header-info h1 {
  font-size: 22px;
  margin: 0;
  color: var(--color-text-primary);
}

.day-badge {
  background: var(--color-type-transport-bg);
  color: var(--color-type-transport);
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 13px;
}

.status-badge {
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 13px;
}
.status-badge.active { background: var(--color-type-attraction-bg); color: var(--color-type-attraction); }
.status-badge.paused { background: var(--color-type-food-bg); color: var(--color-type-food); }
.status-badge.completed { background: var(--color-bg-tertiary); color: var(--color-text-tertiary); }

.header-actions {
  display: flex;
  gap: 8px;
}

.btn {
  padding: 6px 16px;
  border-radius: 6px;
  border: 1px solid var(--color-border);
  cursor: pointer;
  font-size: 14px;
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  transition: all 0.2s ease;
}
.btn-primary {
  background: var(--color-brand-500);
  color: #fff;
  border-color: var(--color-brand-500);
}
.btn-primary:hover {
  background: var(--color-brand-600);
}
.btn-outline {
  background: transparent;
  color: var(--color-text-secondary);
}
.btn-outline:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
}
.btn-success {
  background: var(--color-type-attraction);
  color: #fff;
  border-color: var(--color-type-attraction);
}

.trip-body {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.info-panel {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.info-panel .quick-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
}

.quick-stats {
  background: var(--color-bg-secondary);
  border-radius: 8px;
  padding: 16px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
}

.stat-label {
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.stat-value {
  font-size: 18px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.reminder-banner {
  background: linear-gradient(135deg, var(--color-type-transport-bg), var(--color-type-attraction-bg));
  border: 1px solid var(--color-type-transport);
  border-radius: 10px;
  padding: 14px 18px;
  margin-bottom: 16px;
}

.reminder-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  color: var(--color-text-secondary);
}

.reminder-loading-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-type-transport);
  animation: reminderPulse 1s ease-in-out infinite;
}

@keyframes reminderPulse {
  50% { opacity: 0.35; transform: scale(0.8); }
}
.reminder-text { font-size: 15px; color: var(--color-type-transport-icon); line-height: 1.6; }
.reminder-hint { margin-top: 6px; font-size: 13px; color: var(--color-type-transport); }

.star-rating button {
  background: none;
  border: none;
  font-size: 28px;
  color: var(--color-border);
  cursor: pointer;
  padding: 0 2px;
  transition: color 0.15s;
}
.star-rating button.active,
.star-rating button:hover { color: var(--color-gold); }

.modal-overlay {
  position: fixed;
  inset: 0;
  background: var(--color-overlay);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: var(--z-modal-overlay);
}

.checkin-modal {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  padding: 24px;
  width: 420px;
  max-height: 80vh;
  overflow-y: auto;
  box-shadow: var(--shadow-modal);
}

.checkin-modal h2 {
  color: var(--color-text-primary);
  margin: 0 0 4px;
}

.checkin-poi {
  color: var(--color-text-secondary);
  margin-bottom: 16px;
}

.form-group {
  margin-bottom: 16px;
}
.form-group label {
  display: block;
  margin-bottom: 4px;
  font-weight: 500;
  font-size: 14px;
  color: var(--color-text-primary);
}
.form-group textarea,
.form-group input {
  width: 100%;
  border: 1px solid var(--color-border);
  border-radius: 6px;
  padding: 8px 12px;
  font-size: 14px;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: border-color 0.2s;
}
.form-group textarea:focus,
.form-group input:focus {
  outline: none;
  border-color: var(--color-brand-500);
  box-shadow: var(--input-focus-shadow);
}

.form-actions {
  display: flex;
  gap: 8px;
  justify-content: flex-end;
}

[data-theme="dark"] .reminder-banner {
  border-color: var(--color-type-transport);
  opacity: 0.9;
}
[data-theme="dark"] .status-badge.completed {
  background: var(--color-bg-tertiary);
}
[data-theme="dark"] .checkin-modal {
  border: 1px solid var(--color-border);
}

/* 确认对话框 */
.confirm-dialog {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  padding: 32px 28px 24px;
  width: 380px;
  text-align: center;
  box-shadow: var(--shadow-modal);
}
.confirm-dialog .confirm-icon {
  font-size: 48px;
  margin-bottom: 12px;
}
.confirm-dialog h2 {
  color: var(--color-text-primary);
  margin: 0 0 8px;
  font-size: 20px;
}
.confirm-dialog p {
  color: var(--color-text-secondary);
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 24px;
}
.confirm-dialog .form-actions {
  justify-content: center;
  gap: 12px;
}

/* 天级导航 */
.day-navigator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  overflow-x: auto;
}
.day-arrow {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  color: var(--color-text-primary);
  font-size: 18px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.2s;
}
.day-arrow:hover:not(:disabled) {
  background: var(--color-bg-secondary);
  border-color: var(--color-brand-500);
}
.day-arrow:disabled {
  opacity: 0.3;
  cursor: not-allowed;
}
.day-chips {
  display: flex;
  gap: 6px;
  flex: 1;
  overflow-x: auto;
}
.day-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: 6px 14px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--color-border);
  background: var(--color-bg-card);
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  min-width: 60px;
}
.day-chip:hover {
  border-color: var(--color-brand-400);
}
.day-chip.active {
  background: var(--color-brand-500);
  border-color: var(--color-brand-500);
  color: #fff;
}
.day-chip.current:not(.active) {
  border-color: var(--color-type-attraction);
  background: var(--color-type-attraction-bg);
}
.day-num {
  font-size: 13px;
  font-weight: 500;
}
.day-badge-current {
  font-size: 10px;
  opacity: 0.8;
}
.day-chip.active .day-badge-current {
  color: #fff;
}

/* 当天行程摘要 */
.day-summary-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  margin-bottom: 16px;
  background: var(--color-type-attraction-bg);
  border-radius: var(--radius-sm);
  border-left: 3px solid var(--color-type-attraction);
}
.day-summary-icon { font-size: 16px; flex-shrink: 0; }
.day-summary-text {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
}
</style>
