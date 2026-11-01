<script setup lang="ts">
import { computed } from 'vue'
import BudgetChart from './BudgetChart.vue'

interface BudgetRow {
  category: string
  budget: number
  spent: number
  status: string
}

const props = defineProps<{
  total: number
  estimated: number
  breakdown: Record<string, unknown>
  details?: BudgetRow[]
  warnings?: string[]
  suggestions?: string[]
}>()

const remaining = computed(() => Math.max(props.total - props.estimated, 0))
const usagePercent = computed(() => props.total > 0 ? Math.round(props.estimated / props.total * 100) : 0)
const progressWidth = computed(() => Math.min(usagePercent.value, 100))
const isOverBudget = computed(() => props.total > 0 && props.estimated > props.total)
</script>

<template>
  <aside class="budget-overview-card">
    <div class="budget-overview-card__header">
      <div>
        <span class="budget-overview-card__eyebrow">预算概览</span>
        <h2 class="budget-overview-card__title">
          分布与执行情况
        </h2>
      </div>
      <span
        class="budget-overview-card__status"
        :class="{ 'budget-overview-card__status--over': isOverBudget }"
      >
        {{ isOverBudget ? '已超预算' : '预算内' }}
      </span>
    </div>

    <div class="budget-overview-card__metrics">
      <div class="budget-overview-card__metric budget-overview-card__metric--primary">
        <span>预估花费</span>
        <strong>¥{{ estimated.toFixed(0) }}</strong>
      </div>
      <div class="budget-overview-card__metric">
        <span>总预算</span>
        <strong>¥{{ total.toFixed(0) }}</strong>
      </div>
      <div class="budget-overview-card__metric">
        <span>{{ isOverBudget ? '超出' : '剩余' }}</span>
        <strong>¥{{ (isOverBudget ? estimated - total : remaining).toFixed(0) }}</strong>
      </div>
    </div>

    <div
      v-if="total > 0"
      class="budget-overview-card__progress-wrap"
    >
      <div class="budget-overview-card__progress">
        <div
          class="budget-overview-card__progress-fill"
          :class="{ 'budget-overview-card__progress-fill--over': isOverBudget }"
          :style="{ width: progressWidth + '%' }"
        />
      </div>
      <span>{{ usagePercent }}%</span>
    </div>

    <BudgetChart
      :budget="{ total, breakdown } as any"
      :show-title="false"
      compact
      hide-empty
    />

    <div
      v-if="details?.length"
      class="budget-overview-card__details"
    >
      <div class="budget-overview-card__section-title">
        分类明细
      </div>
      <div
        v-for="item in details"
        :key="item.category"
        class="budget-overview-card__detail-row"
      >
        <span class="budget-overview-card__category">{{ item.category }}</span>
        <span class="budget-overview-card__amount">¥{{ item.spent.toFixed(0) }} / ¥{{ item.budget.toFixed(0) }}</span>
        <span
          class="budget-overview-card__detail-status"
          :class="{ 'budget-overview-card__detail-status--over': item.status === 'over' }"
        >
          {{ item.status === 'over' ? '超支' : '正常' }}
        </span>
      </div>
    </div>

    <div
      v-if="warnings?.length || suggestions?.length"
      class="budget-overview-card__notes"
    >
      <p
        v-for="warning in warnings?.slice(0, 2)"
        :key="warning"
        class="budget-overview-card__note budget-overview-card__note--warning"
      >
        ⚠ {{ warning }}
      </p>
      <p
        v-for="suggestion in suggestions?.slice(0, 2)"
        :key="suggestion"
        class="budget-overview-card__note"
      >
        💡 {{ suggestion }}
      </p>
    </div>
  </aside>
</template>

<style scoped>
.budget-overview-card {
  padding: var(--space-5);
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-float);
}
.budget-overview-card__header,
.budget-overview-card__metrics,
.budget-overview-card__progress-wrap,
.budget-overview-card__detail-row {
  display: flex;
  align-items: center;
}
.budget-overview-card__header { justify-content: space-between; gap: var(--space-3); margin-bottom: var(--space-4); }
.budget-overview-card__eyebrow { display: block; margin-bottom: 2px; color: var(--color-brand-600); font-size: 11px; font-weight: 600; letter-spacing: 0.08em; }
.budget-overview-card__title { margin: 0; color: var(--color-text-primary); font-size: 17px; line-height: 1.3; }
.budget-overview-card__status,
.budget-overview-card__detail-status { padding: 2px 7px; color: var(--color-success); background: color-mix(in srgb, var(--color-success) 12%, transparent); border-radius: 999px; font-size: 11px; white-space: nowrap; }
.budget-overview-card__status--over,
.budget-overview-card__detail-status--over { color: var(--color-error); background: color-mix(in srgb, var(--color-error) 10%, transparent); }
.budget-overview-card__metrics { display: grid; grid-template-columns: 1.3fr 1fr 1fr; gap: var(--space-2); }
.budget-overview-card__metric { display: flex; flex-direction: column; gap: 3px; padding: var(--space-2); background: var(--color-bg-secondary); border-radius: var(--radius-sm); }
.budget-overview-card__metric span { color: var(--color-text-tertiary); font-size: 11px; }
.budget-overview-card__metric strong { color: var(--color-text-primary); font-size: 15px; font-variant-numeric: tabular-nums; }
.budget-overview-card__metric--primary strong { color: var(--color-brand-600); font-size: 19px; }
.budget-overview-card__progress-wrap { gap: var(--space-2); margin: var(--space-3) 0; }
.budget-overview-card__progress { flex: 1; height: 6px; overflow: hidden; background: var(--color-bg-secondary); border-radius: 999px; }
.budget-overview-card__progress-fill { height: 100%; background: var(--color-brand-500); border-radius: inherit; }
.budget-overview-card__progress-fill--over { background: var(--color-error); }
.budget-overview-card__progress-wrap span { min-width: 34px; color: var(--color-text-tertiary); font-size: 11px; text-align: right; }
.budget-overview-card__details { padding-top: var(--space-3); border-top: 1px solid var(--color-border-light); }
.budget-overview-card__section-title { margin-bottom: var(--space-2); color: var(--color-text-secondary); font-size: 12px; font-weight: 600; }
.budget-overview-card__detail-row { gap: var(--space-2); min-height: 28px; font-size: 12px; }
.budget-overview-card__category { flex: 1; color: var(--color-text-secondary); }
.budget-overview-card__amount { color: var(--color-text-primary); font-variant-numeric: tabular-nums; }
.budget-overview-card__notes { display: flex; flex-direction: column; gap: var(--space-1); margin-top: var(--space-3); }
.budget-overview-card__note { margin: 0; padding: var(--space-2); color: var(--color-text-secondary); background: var(--color-brand-50); border-radius: var(--radius-sm); font-size: 11px; line-height: 1.45; }
.budget-overview-card__note--warning { color: var(--color-error); background: color-mix(in srgb, var(--color-error) 7%, transparent); }
</style>
