<script setup lang="ts">
/* ============================================================
   PlanTimeline — 日程标签栏（多选）
   点击标签展开/收起对应日期的卡片
   ============================================================ */

import { computed } from 'vue'

const props = defineProps<{
  dayCount: number
  expandedDays: number[]
  dates?: string[]
  dateLabels?: string[]
}>()

const emit = defineEmits<{
  toggleDay: [day: number]
}>()

const dayItems = computed(() => {
  return Array.from({ length: props.dayCount }, (_, i) => ({
    day: i + 1,
    date: props.dates?.[i] || '',
    label: props.dateLabels?.[i] || '',
  }))
})
</script>

<template>
  <div class="plan-timeline">
    <button
      v-for="item in dayItems"
      :key="item.day"
      class="plan-timeline__item"
      :class="{ 'plan-timeline__item--active': expandedDays.includes(item.day) }"
      @click="emit('toggleDay', item.day)"
    >
      <span class="plan-timeline__day">Day {{ item.day }}</span>
      <span class="plan-timeline__date">{{ item.label || '' }}</span>
      <span class="plan-timeline__date-num">{{ item.date?.slice(5) || '' }}</span>
    </button>
  </div>
</template>

<style scoped>
.plan-timeline {
  display: flex;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-6);
  background: var(--color-bg-primary);
  border-bottom: 1px solid var(--color-border-light);
  overflow-x: auto;
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
}

.plan-timeline__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  padding: var(--space-2) var(--space-4);
  border: none;
  background: transparent;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-in-out);
  min-width: 72px;
  flex-shrink: 0;
}
.plan-timeline__item:hover {
  background: var(--color-brand-50);
}
.plan-timeline__item--active {
  background: var(--color-brand-500);
  color: white;
}
.plan-timeline__item--active:hover {
  background: var(--color-brand-600);
}

.plan-timeline__day {
  font-size: var(--text-caption);
  font-weight: var(--fw-bold);
}

.plan-timeline__date {
  font-size: var(--text-tiny);
  opacity: 0.7;
}

.plan-timeline__date-num {
  font-size: 11px;
  opacity: 0.6;
}
</style>
