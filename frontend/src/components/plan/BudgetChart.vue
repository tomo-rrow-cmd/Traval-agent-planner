<script setup lang="ts">
/* ============================================================
   BudgetChart — 预算占比环形图
   对应文档：前端界面设计文档.md · §8.2
   ============================================================ */

import { computed } from 'vue'
import type { BudgetDetail } from '@/types/plan'

const props = withDefaults(defineProps<{
  budget: BudgetDetail
  showTitle?: boolean
  compact?: boolean
  hideEmpty?: boolean
}>(), {
  showTitle: true,
  compact: false,
  hideEmpty: false,
})

interface CategoryItem {
  key: string
  label: string
  amount: number
  percent: number
  color: string
}

/** 分类定义：key → 中文名 → 颜色 */
const CATEGORY_META: Array<{ key: string; label: string; color: string }> = [
  { key: 'transport', label: '交通', color: '#7EB8DA' },
  { key: 'accommodation', label: '住宿', color: '#B58CB0' },
  { key: 'food', label: '美食', color: '#E8A87C' },
  { key: 'attractions', label: '景点', color: '#5B9B8C' },
  { key: 'souvenirs', label: '纪念品', color: '#D98CB8' },
  { key: 'contingency', label: '备用', color: '#D4A857' },
]

const categories = computed<CategoryItem[]>(() => {
  const b = props.budget.breakdown || {}
  const items = CATEGORY_META.map(({ key, label, color }) => {
    const raw = (b as any)[key]
    // 兼容两种格式：数字（简版） 或 BudgetCategory 对象
    const amount = typeof raw === 'number' ? raw : (raw?.amount ?? 0)
    const percent = typeof raw === 'number' ? 0 : (raw?.percent ?? 0)
    return { key, label, amount, percent, color }
  })
  return props.hideEmpty ? items.filter(item => item.amount > 0) : items
})

/** 计算环形图 SVG stroke-dasharray 和 stroke-dashoffset */
const donutSegments = computed(() => {
  const total = props.budget.total || 1
  const circumference = 2 * Math.PI * 40 // r=40
  let offset = 0
  return categories.value.map((cat) => {
    const ratio = cat.amount / total
    const length = ratio * circumference
    const seg = {
      color: cat.color,
      dasharray: `${length} ${circumference - length}`,
      dashoffset: -offset,
      ratio,
    }
    offset += length
    return seg
  })
})
</script>

<template>
  <div
    class="budget-chart"
    :class="{ 'budget-chart--compact': compact }"
  >
    <h3
      v-if="showTitle"
      class="budget-chart__title"
    >
      预算分布
    </h3>
    <div class="budget-chart__content">
      <div class="budget-chart__donut">
        <svg
          width="120"
          height="120"
          viewBox="0 0 100 100"
        >
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="var(--color-border-light)"
            stroke-width="12"
          />
          <circle
            v-for="(seg, i) in donutSegments"
            :key="i"
            cx="50"
            cy="50"
            r="40"
            fill="none"
            :stroke="seg.color"
            stroke-width="12"
            stroke-linecap="butt"
            :stroke-dasharray="seg.dasharray"
            :stroke-dashoffset="seg.dashoffset"
            transform="rotate(-90, 50, 50)"
            style="transition: all 0.5s ease"
          />
          <text
            x="50"
            y="48"
            text-anchor="middle"
            font-size="14"
            font-weight="700"
            fill="var(--color-text-primary)"
          >
            {{ budget.total ? '¥' + budget.total.toFixed(0) : '暂无' }}
          </text>
          <text
            x="50"
            y="62"
            text-anchor="middle"
            font-size="8"
            fill="var(--color-text-tertiary)"
          >{{ budget.total ? '总预算' : '' }}</text>
        </svg>
      </div>
      <div class="budget-chart__legend">
        <div
          v-for="cat in categories"
          :key="cat.key"
          class="budget-chart__item"
        >
          <span
            class="budget-chart__dot"
            :style="{ background: cat.color }"
          />
          <span class="budget-chart__label">{{ cat.label }}</span>
          <span class="budget-chart__amount">¥{{ cat.amount }}</span>
          <span class="budget-chart__percent">{{ cat.percent }}%</span>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.budget-chart {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  padding: var(--space-5);
  box-shadow: var(--shadow-float);
}
.budget-chart--compact { padding: var(--space-2) 0 var(--space-3); background: transparent; box-shadow: none; }
.budget-chart--compact .budget-chart__content { gap: var(--space-3); }
.budget-chart--compact .budget-chart__item { font-size: 12px; }

.budget-chart__title {
  font-size: var(--text-h4);
  font-weight: var(--fw-semibold);
  margin-bottom: var(--space-4);
}

.budget-chart__content {
  display: flex;
  gap: var(--space-6);
  align-items: center;
}

.budget-chart__donut {
  flex-shrink: 0;
}

.budget-chart__legend {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.budget-chart__item {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-body-sm);
}

.budget-chart__dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}

.budget-chart__label {
  flex: 1;
  color: var(--color-text-secondary);
}

.budget-chart__amount {
  font-weight: var(--fw-semibold);
  color: var(--color-text-primary);
  min-width: 60px;
  text-align: right;
}

.budget-chart__percent {
  color: var(--color-text-tertiary);
  min-width: 36px;
  text-align: right;
}
</style>
