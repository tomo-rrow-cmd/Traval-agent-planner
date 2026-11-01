<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePlanStore } from '@/store/planStore'
import type { DailyItinerary } from '@/types/plan'
import BlockRenderer from '@/components/plan/BlockRenderer.vue'

const router = useRouter()
const planStore = usePlanStore()

const emit = defineEmits<{ collapse: [] }>()

const plan = computed(() => planStore.currentPlan)
const progress = computed(() => planStore.generateProgress)
const progressPercent = computed(() => progress.value?.percent ?? 0)
const progressMessage = computed(() => progress.value?.message ?? '')
const progressStep = computed(() => progress.value?.step ?? '')
const isGenerating = computed(() => planStore.isGenerating)

// content_blocks 优先
const contentBlocks = computed(() => ((plan.value as any)?.content_blocks || []) as any[])
const hasContentBlocks = computed(() => contentBlocks.value.length > 0)

const activeDay = ref(1)
const days = computed(() => plan.value?.daily_itinerary || [])

const currentDay = computed(() => days.value.find((d: DailyItinerary) => d.day === activeDay.value))

function prevDay() { if (activeDay.value > 1) activeDay.value-- }
function nextDay() { if (activeDay.value < days.value.length) activeDay.value++ }

const budgetPercent = computed(() => {
  if (!plan.value?.total_budget) return 0
  return Math.min((plan.value.estimated_cost || 0) / plan.value.total_budget * 100, 100)
})

const stepLabels: Record<string, string> = {
  info_collection: '了解出行需求',
  parallel_planning: '并行规划中',
  route_optimization: '路线优化中',
  modifying: '调整行程中',
}

const previewBlocks = computed(() => {
  // 取 content_blocks 的前几个块用于缩略预览
  const blocks = contentBlocks.value
  const result = []
  for (const b of blocks) {
    if (b.type === 'header') { result.push(b); continue }
    if (b.type === 'day_card' && result.filter(x => x.type === 'day_card').length < 3) { result.push(b); continue }
    if (b.type === 'budget_chart') { result.push(b); continue }
    if (b.type === 'callout' && result.filter(x => x.type === 'callout').length < 1) { result.push(b); continue }
    if (b.type === 'divider') { result.push(b); continue }
    // 最多取 8 个块
    if (result.length >= 8) break
  }
  return result
})
</script>

<template>
  <div class="plan-preview">
    <!-- Header -->
    <div class="pp-header">
      <div class="pp-header__left">
        <svg
          width="18"
          height="18"
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
          /><line
            x1="16"
            y1="2"
            x2="16"
            y2="6"
          /><line
            x1="8"
            y1="2"
            x2="8"
            y2="6"
          /><line
            x1="3"
            y1="10"
            x2="21"
            y2="10"
          />
        </svg>
        <span>实时方案</span>
      </div>
      <button
        class="pp-header__close"
        @click="emit('collapse')"
      >
        ✕
      </button>
    </div>

    <!-- Generating -->
    <div
      v-if="isGenerating"
      class="pp-generating"
    >
      <div class="pp-progress">
        <a-progress
          :percent="progressPercent"
          :show-info="false"
          :stroke-color="'var(--color-brand-500)'"
          size="small"
        />
        <div class="pp-progress__label">
          <span class="pp-progress__dot" />
          {{ stepLabels[progressStep] || progressStep }}
        </div>
        <p class="pp-progress__msg">
          {{ progressMessage }}
        </p>
      </div>
      <div class="pp-skeleton">
        <div
          v-for="i in 3"
          :key="i"
          class="pp-skeleton__card"
        >
          <div
            class="pp-skeleton__line"
            style="width:40%;height:14px"
          />
          <div
            class="pp-skeleton__line"
            style="width:80%;height:10px"
          />
          <div
            class="pp-skeleton__line"
            style="width:60%;height:10px"
          />
        </div>
      </div>
    </div>

    <!-- Plan Ready via content_blocks -->
    <div
      v-else-if="hasContentBlocks"
      class="pp-ready"
    >
      <div class="pp-preview-scroll">
        <BlockRenderer :blocks="previewBlocks" />
      </div>
      <div class="pp-footer">
        <button
          class="pp-footer__btn"
          @click="router.push(`/plans/${plan?.id || (plan as any)?._id || 'detail'}`)"
        >
          查看完整方案 →
        </button>
      </div>
    </div>

    <!-- Plan Ready via daily_itinerary (旧格式) -->
    <div
      v-else-if="plan && days.length > 0"
      class="pp-ready"
    >
      <!-- Trip Summary Card -->
      <div class="pp-summary">
        <div class="pp-summary__route">
          <span class="pp-summary__city">{{ plan.departure || '' }}</span>
          <span class="pp-summary__arrow">→</span>
          <span class="pp-summary__city pp-summary__city--dest">{{ plan.destination }}</span>
        </div>
        <div class="pp-summary__meta">
          <span>📅 {{ plan.days }}天</span>
          <span
            v-if="plan.pace || plan.trip_config?.pace"
            class="pp-summary__dot"
          >·</span>
          <span v-if="plan.pace || plan.trip_config?.pace">{{ plan.pace || plan.trip_config?.pace }}</span>
          <span v-if="plan.people_count"><span class="pp-summary__dot">·</span> {{ plan.people_count }}人</span>
          <span class="pp-summary__dot">·</span>
          <span>💰 ¥{{ plan.total_budget }}</span>
        </div>
        <div class="pp-summary__budget">
          <div class="pp-summary__bar">
            <div
              class="pp-summary__fill"
              :style="{ width: budgetPercent + '%' }"
            />
          </div>
          <div class="pp-summary__stats">
            <span>已花 ¥{{ plan.estimated_cost || 0 }}</span>
            <span>剩余 ¥{{ Math.max((plan.total_budget || 0) - (plan.estimated_cost || 0), 0) }}</span>
          </div>
        </div>
      </div>

      <!-- Day Selector -->
      <div class="pp-days">
        <button
          class="pp-days__btn pp-days__btn--prev"
          :disabled="activeDay <= 1"
          @click="prevDay"
        >
          ‹
        </button>
        <div class="pp-days__tabs">
          <button
            v-for="day in days"
            :key="day.day"
            class="pp-days__tab"
            :class="{ 'pp-days__tab--active': activeDay === day.day }"
            @click="activeDay = day.day"
          >
            Day{{ day.day }}
          </button>
        </div>
        <button
          class="pp-days__btn pp-days__btn--next"
          :disabled="activeDay >= days.length"
          @click="nextDay"
        >
          ›
        </button>
      </div>

      <!-- Day Content -->
      <div
        v-if="currentDay"
        class="pp-timeline"
      >
        <!-- Attractions -->
        <div
          v-for="(act, idx) in (currentDay.activities || currentDay.attractions || [])"
          :key="idx"
          class="pp-timeline__item"
        >
          <div class="pp-timeline__dot pp-timeline__dot--sight" />
          <div class="pp-timeline__card">
            <div class="pp-timeline__header">
              <div class="pp-timeline__title">
                {{ act.title || act.name }}
              </div>
              <span
                v-if="act.rating"
                class="pp-timeline__rating"
              >★ {{ act.rating }}</span>
            </div>
            <div class="pp-timeline__tags">
              <span class="pp-tag pp-tag--time">{{ act.duration_hours ? act.duration_hours + 'h' : (act.duration_minutes ? Math.round(act.duration_minutes / 60) + 'h' : '?') }}</span>
              <span class="pp-tag pp-tag--price">{{ (act.cost ?? act.price) === 0 ? '免费' : '¥' + ((act.cost ?? act.price) || '?') }}</span>
              <span
                v-for="tag in (act.tags || []).slice(0, 2)"
                :key="tag"
                class="pp-tag pp-tag--label"
              >{{ tag }}</span>
            </div>
            <p
              v-if="act.description || act.reason"
              class="pp-timeline__desc"
            >
              {{ act.description || act.reason }}
            </p>
          </div>
        </div>

        <!-- Meals -->
        <div
          v-for="(m, idx) in (currentDay.meals || [])"
          :key="'m'+idx"
          class="pp-timeline__item"
        >
          <div class="pp-timeline__dot pp-timeline__dot--meal" />
          <div class="pp-timeline__card">
            <div class="pp-timeline__title">
              {{ m.restaurant }}
            </div>
            <div class="pp-timeline__tags">
              <span class="pp-tag pp-tag--meal">{{ m.meal }}</span>
              <span class="pp-tag pp-tag--price">{{ m.avg_price ? '¥' + m.avg_price : '' }}</span>
            </div>
            <p
              v-if="m.reason"
              class="pp-timeline__desc"
            >
              {{ m.reason }}
            </p>
          </div>
        </div>

        <!-- Hotel / Accommodation -->
        <div
          v-if="currentDay.accommodation || currentDay.hotel"
          class="pp-timeline__item"
        >
          <div class="pp-timeline__dot pp-timeline__dot--hotel" />
          <div class="pp-timeline__card">
            <div class="pp-timeline__title">
              {{ currentDay.accommodation?.hotel_name || currentDay.hotel?.name }}
            </div>
            <div class="pp-timeline__tags">
              <span class="pp-tag pp-tag--hotel">住宿</span>
              <span
                v-if="currentDay.accommodation?.rating || currentDay.hotel?.rating"
                class="pp-tag pp-tag--rating"
              >★ {{ currentDay.accommodation?.rating || currentDay.hotel?.rating }}</span>
              <span class="pp-tag pp-tag--price">{{ currentDay.accommodation?.price || currentDay.hotel?.price_per_night ? '¥' + (currentDay.accommodation?.price || currentDay.hotel?.price_per_night) + '/晚' : '' }}</span>
            </div>
            <p
              v-if="currentDay.accommodation?.address || currentDay.hotel?.address"
              class="pp-timeline__desc"
            >
              {{ currentDay.accommodation?.address || currentDay.hotel?.address }}
            </p>
          </div>
        </div>

        <!-- Traffic -->
        <div
          v-if="plan.traffic?.daily_traffic?.[activeDay-1]?.total_cost"
          class="pp-timeline__item"
        >
          <div class="pp-timeline__dot pp-timeline__dot--traffic" />
          <div class="pp-timeline__card">
            <div class="pp-timeline__title">
              市内交通
            </div>
            <div class="pp-timeline__desc">
              {{ plan.traffic.daily_traffic[activeDay-1].total_time_min || 0 }}分钟 ·
              ¥{{ plan.traffic.daily_traffic[activeDay-1].total_cost || 0 }}
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Stats -->
      <div class="pp-stats">
        <div class="pp-stats__item">
          <span class="pp-stats__num">{{ days.reduce((s: number, d: any) => s + (d.activities || d.attractions || []).length, 0) }}</span>
          <span class="pp-stats__label">景点</span>
        </div>
        <div class="pp-stats__item">
          <span class="pp-stats__num">{{ days.reduce((s: number, d: any) => s + (d.meals || []).length, 0) }}</span>
          <span class="pp-stats__label">餐饮</span>
        </div>
        <div class="pp-stats__item">
          <span class="pp-stats__num">{{ plan.hotel_plan?.recommendations?.length || 0 }}</span>
          <span class="pp-stats__label">酒店</span>
        </div>
        <div class="pp-stats__item">
          <span class="pp-stats__num">{{ Array.isArray(plan.big_traffic) ? plan.big_traffic.length : plan.big_traffic?.trains?.length || 0 }}</span>
          <span class="pp-stats__label">车次</span>
        </div>
      </div>

      <!-- Budget Details -->
      <div
        v-if="plan.budget?.details?.length"
        class="pp-budget"
      >
        <div
          v-for="d in plan.budget.details.slice(0, 4)"
          :key="d.category"
          class="pp-budget-row"
        >
          <span class="pp-budget-label">{{ d.category }}</span>
          <div class="pp-budget-track">
            <div
              class="pp-budget-fill"
              :style="{ width: Math.min((d.spent / (plan.total_budget || 1)) * 100, 100) + '%' }"
            />
          </div>
          <span class="pp-budget-spent">¥{{ d.spent }}</span>
        </div>
      </div>

      <!-- View Full Plan -->
      <div class="pp-footer">
        <button
          class="pp-footer__btn"
          @click="router.push(`/plans/${plan.id || 'detail'}`)"
        >
          查看完整方案 →
        </button>
      </div>
    </div>

    <!-- Empty -->
    <div
      v-else
      class="pp-empty"
    >
      <svg
        width="40"
        height="40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="#ccc"
        stroke-width="1.5"
      ><circle
        cx="12"
        cy="10"
        r="3"
      /><path d="M12 21.7C17.3 17 20 13 20 10a8 8 0 1 0-16 0c0 3 2.7 7 8 11.7z" /></svg>
      <p>开始对话后，方案将实时显示在这里</p>
    </div>
  </div>
</template>

<style scoped>
.plan-preview {
  height: 100%; display: flex; flex-direction: column;
  background: var(--color-bg-card); border-left: 1px solid var(--color-border);
}

/* Header */
.pp-header {
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 16px; border-bottom: 1px solid var(--color-border-light); flex-shrink: 0;
}
.pp-header__left {
  display: flex; align-items: center; gap: 8px;
  font-size: 15px; font-weight: 600; color: var(--color-text-primary);
}
.pp-header__left svg { color: var(--color-brand-500); }
.pp-header__close {
  width: 28px; height: 28px; border: none; background: var(--color-bg-secondary);
  border-radius: 6px; color: var(--color-text-tertiary); cursor: pointer; font-size: 14px;
}

/* Summary Card */
.pp-ready { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.pp-summary {
  background: linear-gradient(135deg, var(--color-brand-50), var(--color-bg-card));
  padding: 16px; margin: 12px 12px 0; border-radius: 12px;
}
.pp-summary__route {
  display: flex; align-items: center; justify-content: center; gap: 8px;
  font-size: 18px; font-weight: 700; color: var(--color-text-primary); margin-bottom: 6px;
}
.pp-summary__arrow { color: var(--color-brand-500); font-weight: 300; }
.pp-summary__city--dest { color: var(--color-brand-500); }
.pp-summary__meta {
  display: flex; align-items: center; justify-content: center; gap: 4px;
  font-size: 13px; color: var(--color-text-tertiary); margin-bottom: 10px;
}
.pp-summary__budget {}
.pp-summary__bar {
  height: 6px; background: var(--color-bg-tertiary); border-radius: 3px; overflow: hidden;
}
.pp-summary__fill {
  height: 100%; background: linear-gradient(90deg, var(--color-brand-500), var(--color-brand-600));
  border-radius: 3px; transition: width 0.5s ease;
}
.pp-summary__stats {
  display: flex; justify-content: space-between; font-size: 11px; color: var(--color-text-tertiary); margin-top: 4px;
}

/* Day Selector */
.pp-days {
  display: flex; align-items: center; gap: 4px; padding: 8px 12px;
}
.pp-days__tabs {
  display: flex; gap: 4px; flex: 1; overflow-x: auto;
}
.pp-days__tab {
  flex: 1; padding: 6px 0; border: 1px solid var(--color-border); background: var(--color-bg-card);
  border-radius: 6px; font-size: 12px; color: var(--color-text-secondary); cursor: pointer; text-align: center;
}
.pp-days__tab--active { background: var(--color-brand-500); color: #fff; border-color: var(--color-brand-500); font-weight: 600; }
.pp-days__btn {
  width: 28px; height: 28px; border: 1px solid var(--color-border); background: var(--color-bg-card);
  border-radius: 6px; color: var(--color-text-secondary); cursor: pointer; font-size: 16px; flex-shrink: 0;
}
.pp-days__btn:disabled { opacity: 0.3; cursor: default; }

/* Timeline */
.pp-timeline {
  flex: 1; overflow-y: auto; padding: 0 16px 12px;
}
.pp-timeline__item {
  display: flex; gap: 12px; margin-bottom: 12px;
}
.pp-timeline__dot {
  width: 12px; height: 12px; border-radius: 50%; margin-top: 14px; flex-shrink: 0;
}
.pp-timeline__dot--sight { background: var(--color-brand-500); }
.pp-timeline__dot--meal { background: var(--color-type-transport); }
.pp-timeline__dot--hotel { background: var(--color-type-attraction); }
.pp-timeline__dot--traffic { background: var(--color-type-entertainment); }
.pp-timeline__card {
  flex: 1; background: var(--color-bg-secondary); border-radius: 10px; padding: 10px 12px;
}
.pp-timeline__title {
  font-size: 14px; font-weight: 600; color: var(--color-text-primary); margin-bottom: 4px;
}
.pp-timeline__header {
  display: flex; align-items: center; justify-content: space-between; gap: 6px; margin-bottom: 4px;
}
.pp-timeline__rating {
  font-size: 12px; font-weight: 600; color: var(--color-gold, #D4A857); white-space: nowrap; flex-shrink: 0;
}
.pp-timeline__tags { display: flex; gap: 6px; margin-bottom: 4px; flex-wrap: wrap; }
.pp-tag {
  font-size: 11px; padding: 1px 8px; border-radius: 4px;
}
.pp-tag--time { background: var(--color-type-food-bg); color: var(--color-brand-600); }
.pp-tag--price { background: var(--color-type-attraction-bg); color: var(--color-type-attraction); }
.pp-tag--meal { background: var(--color-type-transport-bg); color: var(--color-type-transport); }
.pp-tag--hotel { background: var(--color-type-accommodation-bg); color: var(--color-type-accommodation); }
.pp-tag--label { background: var(--color-brand-50); color: var(--color-brand-600); }
.pp-tag--rating { background: var(--color-gold-bg, #FDF6E3); color: var(--color-gold, #D4A857); }
.pp-timeline__desc { font-size: 12px; color: var(--color-text-tertiary); line-height: 1.5; margin: 0; }

/* Budget Details */
.pp-budget { padding: 10px 16px 6px; border-top: 1px solid var(--color-border-light); }
.pp-budget-row { display: flex; align-items: center; gap: 8px; margin-bottom: 5px; font-size: 12px; }
.pp-budget-label { width: 36px; color: var(--color-text-secondary); flex-shrink: 0; }
.pp-budget-track { flex: 1; height: 5px; background: var(--color-bg-tertiary); border-radius: 3px; overflow: hidden; }
.pp-budget-fill { height: 100%; background: var(--color-brand-300); border-radius: 3px; transition: width 0.5s ease; }
.pp-budget-spent { width: 50px; text-align: right; color: var(--color-text-tertiary); font-size: 11px; }

/* Stats Bar */
.pp-stats {
  display: flex; border-top: 1px solid var(--color-border-light); flex-shrink: 0;
}
.pp-stats__item {
  flex: 1; text-align: center; padding: 10px 0;
}
.pp-stats__num { display: block; font-size: 18px; font-weight: 700; color: var(--color-brand-500); }
.pp-stats__label { font-size: 11px; color: var(--color-text-tertiary); }
.pp-footer { padding: 8px 16px 12px; flex-shrink: 0; display: flex; justify-content: center; }
.pp-footer__btn {
  width: 33.33%; min-width: 120px; max-width: 200px; padding: 8px 0; border: none; background: var(--color-brand-500); color: #fff;
  border-radius: 8px; font-size: 13px; font-weight: 600; cursor: pointer;
  transition: background 0.2s;
}
.pp-footer__btn:hover { background: var(--color-brand-600); }

/* Generating */
.pp-generating { flex: 1; overflow-y: auto; padding: 16px; }

.pp-preview-scroll {
  flex: 1; overflow-y: auto; padding: 8px 12px;
}
.pp-progress {
  background: var(--color-brand-50); border: 1px solid var(--color-brand-100); border-radius: 12px; padding: 16px; margin-bottom: 16px;
}
.pp-progress__label {
  display: flex; align-items: center; gap: 6px;
  font-size: 13px; font-weight: 600; color: var(--color-brand-600); margin-top: 10px;
}
.pp-progress__dot {
  width: 8px; height: 8px; border-radius: 50%; background: var(--color-brand-500);
  animation: pulse 1.5s ease infinite;
}
@keyframes pulse { 0%,100% { opacity: 1 } 50% { opacity: 0.4 } }
.pp-progress__msg { font-size: 12px; color: var(--color-text-tertiary); margin: 4px 0 0; }
.pp-skeleton { display: flex; flex-direction: column; gap: 12px; }
.pp-skeleton__card {
  background: var(--color-bg-secondary); border-radius: 10px; padding: 14px; display: flex; flex-direction: column; gap: 8px;
}
.pp-skeleton__line { background: var(--color-bg-tertiary); border-radius: 4px; animation: shimmer 1.5s ease infinite; }
@keyframes shimmer { 0% { opacity: 1 } 50% { opacity: 0.5 } 100% { opacity: 1 } }

/* Empty */
.pp-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 32px; text-align: center;
}
.pp-empty p { font-size: 13px; color: var(--color-text-tertiary); margin: 12px 0 0; }
</style>
