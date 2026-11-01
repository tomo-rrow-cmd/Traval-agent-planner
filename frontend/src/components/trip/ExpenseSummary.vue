<script setup lang="ts">
/**
 * ExpenseSummary — 花费汇总组件
 */
defineProps<{
  budgetTotal: number
  budgetSpent: number
  budgetRemain: number
}>()
</script>

<template>
  <div class="expense-summary">
    <h3>💰 预算追踪</h3>
    <div class="expense-bar">
      <div class="bar-bg">
        <div
          class="bar-fill"
          :style="{ width: Math.min(100, (budgetSpent / Math.max(budgetTotal, 1)) * 100) + '%' }"
          :class="{ over: budgetSpent > budgetTotal }"
        />
      </div>
    </div>
    <div class="expense-numbers">
      <div class="num-item">
        <span class="num-label">已花</span>
        <span class="num-value spent">¥{{ budgetSpent.toFixed(0) }}</span>
      </div>
      <div class="num-item">
        <span class="num-label">预算</span>
        <span class="num-value">¥{{ budgetTotal.toFixed(0) }}</span>
      </div>
      <div class="num-item">
        <span class="num-label">剩余</span>
        <span :class="['num-value', budgetRemain < 0 ? 'negative' : 'positive']">
          ¥{{ budgetRemain.toFixed(0) }}
        </span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.expense-summary {
  background: var(--color-bg-card);
  border-radius: var(--radius-sm);
  padding: 16px;
}

h3 { margin: 0 0 12px; font-size: 15px; color: var(--color-text-primary); }

.expense-bar { margin-bottom: 12px; }

.bar-bg {
  height: 8px;
  background: var(--color-bg-tertiary);
  border-radius: 4px;
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  background: var(--color-type-attraction);
  border-radius: 4px;
  transition: width 0.5s ease;
}

.bar-fill.over {
  background: var(--color-error);
}

.expense-numbers {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
}

.num-item { text-align: center; }

.num-label {
  display: block;
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.num-value {
  font-size: 16px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.spent { color: var(--color-type-food); }
.positive { color: var(--color-type-attraction); }
.negative { color: var(--color-error); }
</style>
