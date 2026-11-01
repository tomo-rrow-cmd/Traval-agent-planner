<script setup lang="ts">
/**
 * TripTimeline — 当日行程时间线组件
 *
 * 展示签到记录的时间线，区分计划 vs 实际，
 * 支持点击未签到项触发签到流程
 */
import { computed, ref, watch } from 'vue'
import type { CheckinRecord } from '@/api/trip'
import CheckInButton from './CheckInButton.vue'

const props = defineProps<{
  checkins: CheckinRecord[]
  currentDay: number
  /** 当日行程 POI 列表（来自方案），用于动态生成时间线 */
  planSlots?: Array<{ time: string; type: string; name: string }>
}>()

const emit = defineEmits<{
  checkin: [type: string, name: string]
}>()

const FALLBACK_SLOTS = [
  { time: '08:00', type: 'attraction', name: '景点签到' },
  { time: '12:00', type: 'restaurant', name: '午餐签到' },
  { time: '14:00', type: 'attraction', name: '景点签到' },
  { time: '18:00', type: 'restaurant', name: '晚餐签到' },
  { time: '20:00', type: 'hotel', name: '回酒店' },
]

// 动态时间线：切换日期时重新读取最新的 planSlots
const timelineSlots = computed(() => (
  props.planSlots?.length ? props.planSlots : FALLBACK_SLOTS
))

// 模糊匹配 — 同时用 poi_name 和 poi_type 联合判断
function getSlotStatus(name: string, type: string): 'done' | 'pending' {
  const normalizedType = normalizeType(type)
  return props.checkins.some(c => {
    if (c.poi_name === name) return true
    if (c.poi_name && name && (c.poi_name.includes(name) || name.includes(c.poi_name))) {
      return normalizeType(c.poi_type) === normalizedType
    }
    return false
  }) ? 'done' : 'pending'
}

function normalizeType(t: string): string {
  if (t === 'food') return 'restaurant'
  return t
}

function getIcon(type: string): string {
  return type === 'attraction' ? '🏯' :
         type === 'food' || type === 'restaurant' ? '🍜' :
         type === 'hotel' ? '🏨' : '📍'
}

// 高亮最新签到项
const lastSignedPoi = ref('')
watch(
  () => props.checkins,
  checkins => { lastSignedPoi.value = checkins[0]?.poi_name || '' },
  { immediate: true },
)
</script>

<template>
  <div class="trip-timeline">
    <h3>今日行程</h3>

    <div class="timeline-list">
      <div
        v-for="(slot, index) in timelineSlots"
        :key="`${currentDay}:${slot.type}:${slot.name}`"
        :class="['timeline-item', getSlotStatus(slot.name, slot.type), { freshly: slot.name === lastSignedPoi }]"
      >
        <div class="timeline-dot">
          <span class="dot-icon">{{ getIcon(slot.type) }}</span>
        </div>
        <div class="timeline-content">
          <span class="time">{{ slot.time }}</span>
          <span class="name">{{ slot.name }}</span>
          <span
            v-if="getSlotStatus(slot.name, slot.type) === 'done'"
            class="done-mark"
          >✓</span>
          <CheckInButton
            v-else
            :poi-type="slot.type"
            :poi-name="slot.name"
            @checkin="({ type, name }) => emit('checkin', type, name)"
          />
        </div>
        <div
          v-if="index < timelineSlots.length - 1"
          class="timeline-line"
        />
      </div>
    </div>

    <!-- Checkin records -->
    <div
      v-if="checkins.length > 0"
      class="checkin-log"
    >
      <h4>签到记录</h4>
      <div
        v-for="c in checkins.slice(0, 10)"
        :key="c.id"
        class="log-item"
      >
        <span class="log-icon">{{ getIcon(c.poi_type) }}</span>
        <span class="log-name">{{ c.poi_name }}</span>
        <span class="log-time">{{ c.actual_at?.slice(11, 16) ?? '' }}</span>
        <span
          v-if="c.rating"
          class="log-rating"
        >{{ '★'.repeat(c.rating) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.trip-timeline {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  padding: 20px;
}

h3 { margin: 0 0 16px; font-size: 18px; color: var(--color-text-primary); }

.timeline-list {
  position: relative;
}

.timeline-item {
  display: flex;
  gap: 12px;
  padding-bottom: 20px;
  position: relative;
}

.timeline-dot {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  flex-shrink: 0;
}

.timeline-item.done .timeline-dot {
  background: var(--color-type-attraction-bg);
}

.timeline-content {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 8px;
  padding-top: 4px;
}

.time {
  font-size: 13px;
  color: var(--color-text-tertiary);
  width: 40px;
}

.name {
  flex: 1;
  font-size: 14px;
  color: var(--color-text-primary);
}

.done-mark {
  color: var(--color-type-attraction);
  font-weight: bold;
}

.timeline-line {
  position: absolute;
  left: 15px;
  top: 32px;
  bottom: 0;
  width: 2px;
  background: var(--color-border-light);
}

.timeline-item.done + .timeline-item .timeline-line {
  background: var(--color-type-attraction);
  opacity: 0.5;
}

/* 签到后高亮 */
.timeline-item.freshly .timeline-dot {
  box-shadow: 0 0 0 4px var(--color-type-attraction);
  opacity: 0.5;
  transition: box-shadow 0.3s;
}

/* Checkin Log */
.checkin-log {
  margin-top: 20px;
  border-top: 1px solid var(--color-border-light);
  padding-top: 16px;
}

h4 { margin: 0 0 12px; font-size: 15px; color: var(--color-text-primary); }

.log-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 0;
  font-size: 13px;
}

.log-name { flex: 1; color: var(--color-text-primary); }
.log-time { color: var(--color-text-tertiary); }
.log-rating { color: var(--color-gold); }
</style>
