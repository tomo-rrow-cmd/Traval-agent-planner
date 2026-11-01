<script setup lang="ts">
/**
 * AdjustmentBanner — 调整建议横幅
 *
 * 显示天气/时间/预算触发的待处理调整，支持接受/拒绝
 */
import type { AdjustmentRecord } from '@/api/trip'

defineProps<{
  adjustments: AdjustmentRecord[]
}>()

const emit = defineEmits<{
  accept: [id: string]
  reject: [id: string]
}>()

function triggerLabel(type: string): string {
  const map: Record<string, string> = {
    weather: '🌧️ 天气变化',
    time_drift: '⏰ 时间偏离',
    budget_alert: '💰 预算预警',
    user_request: '📝 手动调整',
  }
  return map[type] ?? type
}
</script>

<template>
  <div
    v-if="adjustments.length > 0"
    class="adjustment-banner"
  >
    <div
      v-for="adj in adjustments"
      :key="adj.id"
      class="adj-card"
    >
      <div class="adj-header">
        <span class="adj-trigger">{{ triggerLabel(adj.trigger_type) }}</span>
        <span class="adj-status">待处理</span>
      </div>
      <p class="adj-reason">
        {{ adj.reason }}
      </p>
      <div class="adj-actions">
        <button
          class="btn-accept"
          @click="emit('accept', adj.id)"
        >
          接受
        </button>
        <button
          class="btn-reject"
          @click="emit('reject', adj.id)"
        >
          忽略
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.adjustment-banner {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.adj-card {
  background: var(--color-type-food-bg);
  border: 1px solid var(--color-type-food);
  border-radius: var(--radius-sm);
  padding: 12px 16px;
}

.adj-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.adj-trigger {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-primary);
}

.adj-status {
  background: var(--color-type-food);
  color: #fff;
  padding: 1px 8px;
  border-radius: 10px;
  font-size: 11px;
}

.adj-reason {
  color: var(--color-text-secondary);
  font-size: 13px;
  margin: 0 0 10px;
}

.adj-actions {
  display: flex;
  gap: 8px;
}

.btn-accept {
  padding: 4px 14px;
  border: none;
  border-radius: 4px;
  background: var(--color-brand-500);
  color: #fff;
  cursor: pointer;
  font-size: 13px;
  transition: background 0.2s;
}
.btn-accept:hover {
  background: var(--color-brand-600);
}

.btn-reject {
  padding: 4px 14px;
  border: 1px solid var(--color-border);
  border-radius: 4px;
  background: var(--color-bg-card);
  color: var(--color-text-tertiary);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.btn-reject:hover {
  background: var(--color-bg-secondary);
  color: var(--color-text-primary);
}
</style>
