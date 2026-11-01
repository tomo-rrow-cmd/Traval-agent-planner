<script setup lang="ts">
/* ============================================================
   PlanHeader — 方案概览头部（毛玻璃吸附效果）
   对应文档：界面视觉设计系统.md · §7 毛玻璃、§8.2 方案详情页布局
   ============================================================ */

import type { PlanDetail } from '@/types/plan'

defineProps<{
  plan: PlanDetail
}>()

const emit = defineEmits<{
  favorite: []
  share: []
  export_: []
}>()
</script>

<template>
  <div class="plan-header">
    <div class="plan-header__info">
      <h1 class="plan-header__title">
        {{ plan.title }}
      </h1>
      <div class="plan-header__meta">
        <span class="plan-header__destination">{{ plan.destination }}</span>
        <span class="plan-header__separator">|</span>
        <span>{{ plan.start_date }} ~ {{ plan.end_date }}</span>
        <span class="plan-header__separator">|</span>
        <span>{{ plan.days }}天</span>
        <span class="plan-header__separator">|</span>
        <span>{{ plan.people_count }}人</span>
        <span
          v-if="plan.crowd_type || plan.travel_style"
          class="plan-header__separator"
        >|</span>
        <span v-if="plan.crowd_type || plan.travel_style">{{ plan.crowd_type || plan.travel_style }}</span>
      </div>
    </div>
    <div class="plan-header__actions">
      <div class="plan-header__cost">
        <span class="plan-header__cost-label">预估总费用</span>
        <span class="plan-header__cost-value">¥{{ plan.estimated_cost?.toFixed(0) }}</span>
      </div>
      <a-button
        class="plan-header__action-btn"
        @click="emit('favorite')"
      >
        <template #icon>
          <svg
            :fill="plan.is_favorite ? '#E8A87C' : 'none'"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            stroke="#E8A87C"
            stroke-width="2"
          ><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" /></svg>
        </template>
        收藏
      </a-button>
      <a-button
        class="plan-header__action-btn"
        @click="emit('share')"
      >
        <template #icon>
          🔗
        </template>
        分享
      </a-button>
      <a-button
        class="plan-header__action-btn"
        @click="emit('export_')"
      >
        <template #icon>
          📥
        </template>
        导出
      </a-button>
    </div>
  </div>
</template>

<style scoped>
.plan-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-6);
  padding: var(--space-4) var(--space-6);
  background: var(--color-glass-bg);
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid var(--color-glass-border);
  flex-wrap: wrap;
}

.plan-header__title {
  font-size: var(--text-h3);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-1);
}

.plan-header__meta {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-body-sm);
  color: var(--color-text-secondary);
  flex-wrap: wrap;
}

.plan-header__separator {
  color: var(--color-border);
}

.plan-header__actions {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  flex-shrink: 0;
}

.plan-header__cost {
  text-align: right;
  padding-right: var(--space-4);
  border-right: 1px solid var(--color-border);
}

.plan-header__cost-label {
  display: block;
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
}

.plan-header__cost-value {
  display: block;
  font-size: var(--text-h4);
  font-weight: var(--fw-bold);
  color: var(--color-brand-600);
}

.plan-header__action-btn {
  border-color: var(--color-border) !important;
  color: var(--color-text-secondary) !important;
  border-radius: var(--radius-sm) !important;
}
.plan-header__action-btn:hover {
  border-color: var(--color-brand-300) !important;
  color: var(--color-brand-600) !important;
}
</style>
