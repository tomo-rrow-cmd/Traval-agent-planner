<script setup lang="ts">
/* ============================================================
   PlanListPage — 我的方案（杂志风格方案列表）
   含吸顶Bar + 统计摘要 + 筛选标签 + 入场动画
   ============================================================ */

import { onMounted, ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { usePlanStore } from '@/store/planStore'
import { useUiStore } from '@/store/uiStore'
import PlanCard from '@/components/plan/PlanCard.vue'
import LoadingSpinner from '@/components/common/LoadingSpinner.vue'
import type { PlanSummary } from '@/types/plan'

const router = useRouter()
const planStore = usePlanStore()
const uiStore = useUiStore()

const loading = ref(true)
const currentPage = ref(1)
const pageSize = ref(12)
const activeFilter = ref<'all' | 'fav'>('all')

// 本地测试数据（planStore 数据为空时使用）
const testPlans = ref([
  { id: 'test_1', title: '长沙7日深度游', destination: '长沙', days: 7, estimated_cost: 3932, start_date: '2026-07-10', end_date: '2026-07-16', travel_style: 'relaxed', status: 'completed' as const, is_favorite: true, created_at: '2026-07-09T10:00:00Z' },
  { id: 'test_2', title: '北京3日文化之旅', destination: '北京', days: 3, estimated_cost: 2140, start_date: '2026-08-05', end_date: '2026-08-07', travel_style: 'culture', status: 'completed' as const, is_favorite: false, created_at: '2026-07-08T14:30:00Z' },
  { id: 'test_3', title: '成都美食5日行', destination: '成都', days: 5, estimated_cost: 3200, start_date: '2026-08-15', end_date: '2026-08-19', travel_style: 'food', status: 'completed' as const, is_favorite: false, created_at: '2026-07-07T09:15:00Z' },
  { id: 'test_4', title: '杭州4日休闲游', destination: '杭州', days: 4, estimated_cost: 4400, start_date: '2026-09-01', end_date: '2026-09-04', travel_style: 'relaxed', status: 'completed' as const, is_favorite: true, created_at: '2026-07-06T11:20:00Z' },
  { id: 'test_5', title: '西安3日探险之旅', destination: '西安', days: 3, estimated_cost: 1820, start_date: '2026-09-20', end_date: '2026-09-22', travel_style: 'adventure', status: 'completed' as const, is_favorite: false, created_at: '2026-07-05T16:45:00Z' },
  { id: 'test_6', title: '厦门5日海滨假日', destination: '厦门', days: 5, estimated_cost: 5700, start_date: '2026-10-01', end_date: '2026-10-05', travel_style: 'relaxed', status: 'completed' as const, is_favorite: false, created_at: '2026-07-04T08:30:00Z' },
  { id: 'test_7', title: '云南8日全景环游', destination: '昆明/大理/丽江', days: 8, estimated_cost: 6800, start_date: '2026-10-15', end_date: '2026-10-22', travel_style: 'intensive', status: 'completed' as const, is_favorite: false, created_at: '2026-07-03T13:10:00Z' },
  { id: 'test_8', title: '重庆3日山城探索', destination: '重庆', days: 3, estimated_cost: 1560, start_date: '2026-11-01', end_date: '2026-11-03', travel_style: 'adventure', status: 'completed' as const, is_favorite: true, created_at: '2026-07-02T10:50:00Z' },
  { id: 'test_9', title: '三亚7日滨海度假', destination: '三亚', days: 7, estimated_cost: 8200, start_date: '2026-11-20', end_date: '2026-11-26', travel_style: 'relaxed', status: 'draft' as const, is_favorite: false, created_at: '2026-07-01T09:00:00Z' },
])

/** 根据筛选过滤方案 */
const filteredPlans = computed(() => {
  const plans = planStore.plans.length > 0 ? planStore.plans : testPlans.value
  if (activeFilter.value === 'fav') return plans.filter((p: PlanSummary) => p.is_favorite)
  return plans
})

/** 统计摘要 */
const totalPlans = computed(() => planStore.total || filteredPlans.value.length)
const favCount = computed(() => filteredPlans.value.filter((p: any) => p.is_favorite).length)

onMounted(async () => {
  loading.value = false
})

function goToDetail(planId: string) {
  router.push(`/plans/${planId}`)
}

async function handleFavorite(planId: string) {
  await planStore.toggleFavorite(planId)
}

function setFilter(filter: 'all' | 'fav') {
  activeFilter.value = filter
}

async function handlePageChange(page: number) {
  currentPage.value = page
  try {
    await planStore.fetchPlans(page, pageSize.value)
  } catch {
    uiStore.showError('加载失败')
  }
}
</script>

<template>
  <div class="plan-list-page">
    <!-- ===== 顶部吸顶 Bar ===== -->
    <div class="plan-list-page__bar">
      <div class="plan-list-page__bar-inner">
        <div class="plan-list-page__bar-left">
          <h1 class="plan-list-page__title">
            我的方案
          </h1>
          <span class="plan-list-page__subtitle">已保存的旅行规划</span>
        </div>
        <div class="plan-list-page__stats">
          <div class="plan-list-page__stat-item">
            <span class="plan-list-page__stat-value">{{ totalPlans }}</span>
            <span class="plan-list-page__stat-label">总计</span>
          </div>
          <div class="plan-list-page__stat-divider" />
          <div class="plan-list-page__stat-item">
            <span class="plan-list-page__stat-value">{{ favCount }}</span>
            <span class="plan-list-page__stat-label">收藏</span>
          </div>
        </div>
      </div>
    </div>

    <!-- ===== 筛选标签行 ===== -->
    <div class="plan-list-page__filters">
      <button
        class="plan-list-page__filter-btn"
        :class="{ 'plan-list-page__filter-btn--active': activeFilter === 'all' }"
        @click="setFilter('all')"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <rect
            x="3"
            y="3"
            width="7"
            height="7"
          /><rect
            x="14"
            y="3"
            width="7"
            height="7"
          /><rect
            x="3"
            y="14"
            width="7"
            height="7"
          /><rect
            x="14"
            y="14"
            width="7"
            height="7"
          />
        </svg>
        全部
      </button>
      <button
        class="plan-list-page__filter-btn"
        :class="{ 'plan-list-page__filter-btn--active': activeFilter === 'fav' }"
        @click="setFilter('fav')"
      >
        <svg
          width="14"
          height="14"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
        >
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
        收藏
      </button>
      <div class="plan-list-page__filter-spacer" />
      <span
        v-if="filteredPlans.length > 0"
        class="plan-list-page__filter-hint"
      >
        共 {{ filteredPlans.length }} 个方案
      </span>
    </div>

    <!-- ===== 内容区 ===== -->
    <LoadingSpinner v-if="loading" />

    <!-- 空状态 -->
    <div
      v-else-if="planStore.plans.length === 0 && testPlans.length === 0"
      class="plan-list-page__empty"
    >
      <div class="plan-list-page__empty-icon">
        <svg
          width="48"
          height="48"
          viewBox="0 0 24 24"
          fill="none"
          stroke="var(--color-brand-300)"
          stroke-width="1.5"
          stroke-linecap="round"
        >
          <path d="M3 7v14l6-3 6 3 6-3V4l-6 3-6-3-6 3zM9 4v14M15 7v14" />
        </svg>
      </div>
      <h3 class="plan-list-page__empty-title">
        还没有旅行方案
      </h3>
      <p class="plan-list-page__empty-desc">
        开始一段对话，让 AI 为您规划精彩旅程
      </p>
      <button
        class="plan-list-page__empty-btn"
        @click="router.push('/chat')"
      >
        开始规划旅程 →
      </button>
    </div>

    <!-- 方案网格 -->
    <div
      v-else
      class="plan-list-page__content"
    >
      <TransitionGroup
        name="card-stagger"
        tag="div"
        class="plan-list-page__grid"
      >
        <div
          v-for="(plan, idx) in filteredPlans"
          :key="plan.id"
          :style="{ '--stagger': idx }"
        >
          <PlanCard
            :plan="plan"
            @click="goToDetail(plan.id)"
            @favorite="handleFavorite(plan.id)"
          />
        </div>
      </TransitionGroup>
    </div>

    <!-- 分页器 -->
    <div
      v-if="filteredPlans.length > 0"
      class="plan-list-page__pagination"
    >
      <a-pagination
        :current="currentPage"
        :page-size="pageSize"
        :total="planStore.total"
        show-less-items
        @change="handlePageChange"
      />
    </div>
  </div>
</template>

<style scoped>
.plan-list-page {
  max-width: var(--container-wide);
  margin: 0 auto;
  padding: 0 var(--space-6) var(--space-10);
}

/* ===== 顶部吸顶 Bar ===== */
.plan-list-page__bar {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  background: var(--color-glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--color-glass-border);
  margin: 0 calc(-1 * var(--space-6));
  padding: var(--space-4) var(--space-6);
  transition: background var(--dur-normal) var(--ease-in-out);
}

.plan-list-page__bar-inner {
  display: flex;
  align-items: center;
  justify-content: space-between;
  max-width: var(--container-wide);
  margin: 0 auto;
}

.plan-list-page__bar-left {
  display: flex;
  align-items: baseline;
  gap: var(--space-3);
}

.plan-list-page__title {
  font-size: var(--text-h2);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
  margin: 0;
}

.plan-list-page__subtitle {
  font-size: var(--text-body-sm);
  color: var(--color-text-tertiary);
}

/* 顶部统计 */
.plan-list-page__stats {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.plan-list-page__stat-item {
  display: flex;
  align-items: baseline;
  gap: 4px;
}

.plan-list-page__stat-value {
  font-size: var(--text-h4);
  font-weight: var(--fw-bold);
  color: var(--color-brand-500);
}

.plan-list-page__stat-label {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
}

.plan-list-page__stat-divider {
  width: 1px;
  height: 20px;
  background: var(--color-border-light);
}

/* ===== 筛选行 ===== */
.plan-list-page__filters {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-6);
  padding-top: var(--space-5);
}

.plan-list-page__filter-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  border: 1px solid var(--color-border);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: var(--text-body-sm);
  font-weight: var(--fw-medium);
  border-radius: var(--radius-pill);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-in-out);
}
.plan-list-page__filter-btn:hover {
  border-color: var(--color-brand-300);
  color: var(--color-brand-600);
}
.plan-list-page__filter-btn--active {
  background: var(--color-brand-50);
  border-color: var(--color-brand-400);
  color: var(--color-brand-700);
}

.plan-list-page__filter-spacer {
  flex: 1;
}

.plan-list-page__filter-hint {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
}

/* ===== 空状态 ===== */
.plan-list-page__empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-16) var(--space-4);
  text-align: center;
}

.plan-list-page__empty-icon {
  width: 80px;
  height: 80px;
  border-radius: var(--radius-full);
  background: var(--color-brand-50);
  display: flex;
  align-items: center;
  justify-content: center;
  margin-bottom: var(--space-5);
}

.plan-list-page__empty-title {
  font-size: var(--text-h4);
  font-weight: var(--fw-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.plan-list-page__empty-desc {
  font-size: var(--text-body-sm);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-6);
}

.plan-list-page__empty-btn {
  display: inline-flex;
  padding: 10px 24px;
  border: none;
  background: var(--gradient-gold);
  color: white;
  font-size: var(--text-body);
  font-weight: var(--fw-semibold);
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all 0.3s var(--ease-out-expo);
  box-shadow: var(--shadow-glow-brand);
}
.plan-list-page__empty-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(232, 168, 124, 0.35);
}

/* ===== 方案网格 ===== */
.plan-list-page__content {
  min-height: 200px;
}

.plan-list-page__grid {
  display: grid !important;
  grid-template-columns: repeat(4, 1fr) !important;
  gap: var(--space-4);
}

/* ===== 入场动画（stagger） ===== */
.card-stagger-enter-active {
  transition: all 0.45s var(--ease-out-expo);
  transition-delay: calc(var(--stagger, 0) * 0.06s);
}
.card-stagger-leave-active {
  transition: all 0.25s var(--ease-in-out);
}
.card-stagger-enter-from {
  opacity: 0;
  transform: translateY(20px);
}
.card-stagger-leave-to {
  opacity: 0;
  transform: translateY(-10px) scale(0.95);
}

/* ===== 分页器 ===== */
.plan-list-page__pagination {
  display: flex;
  justify-content: center;
  margin-top: var(--space-8);
  padding: var(--space-4) 0;
}

/* 响应式：窄屏减少列数 */
@media (max-width: 1200px) {
  .plan-list-page__grid {
    grid-template-columns: repeat(3, 1fr);
  }
}
@media (max-width: 900px) {
  .plan-list-page__grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
@media (max-width: 600px) {
  .plan-list-page__grid {
    grid-template-columns: 1fr;
  }
}

/* 滚动条留白 */
@media (max-width: 1024px) {
  .plan-list-page__bar {
    margin: 0;
    padding: var(--space-4) var(--space-4);
  }
}
</style>
