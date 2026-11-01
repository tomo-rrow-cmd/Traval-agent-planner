<script setup lang="ts">
/* ============================================================
   ActivityItem — 活动项（7种类型色标识）
   对应文档：界面视觉设计系统.md · §13 活动类型视觉标识系统
   ============================================================ */

import { ref } from 'vue'
import type { DayActivity, ActivityType } from '@/types/plan'
import { ACTIVITY_TYPE_LABELS } from '@/types/plan'
import IconTravel from '@/components/icons/IconTravel.vue'

const props = defineProps<{
  activity: DayActivity
}>()

const emit = defineEmits<{
  replace: []
  remove: []
}>()

const expanded = ref(false)

const typeColors: Record<ActivityType, { bar: string; dot: string }> = {
  transport: { bar: '#7EB8DA', dot: '#7EB8DA' },
  attraction: { bar: '#5B9B8C', dot: '#5B9B8C' },
  food: { bar: '#E8A87C', dot: '#E8A87C' },
  shopping: { bar: '#D98CB8', dot: '#D98CB8' },
  rest: { bar: '#A8B5A0', dot: '#A8B5A0' },
  entertainment: { bar: '#D4A857', dot: '#D4A857' },
  accommodation: { bar: '#B58CB0', dot: '#B58CB0' },
}

const fallbackColor = { bar: '#A8B5A0', dot: '#A8B5A0' }
const colors = typeColors[props.activity.type] || fallbackColor
const typeLabel = ACTIVITY_TYPE_LABELS[props.activity.type] || '其他'

const typeIcons: Record<string, string> = {
  transport: 'plane', attraction: 'landmark', food: 'sparkle',
  shopping: 'star', rest: 'moon', entertainment: 'compass', accommodation: 'pin',
}
const typeIcon = typeIcons[props.activity.type] || '📍'
</script>

<template>
  <div
    class="activity-item"
    :style="{ '--cyan-color': colors.bar }"
    @click="expanded = !expanded"
  >
    <div
      class="activity-item__dot"
      :style="{ background: colors.dot }"
    />
    <div class="activity-item__body">
      <div class="activity-item__header">
        <span class="activity-item__time">{{ activity.time_slot }}</span>
        <span
          class="activity-item__type-tag"
          :style="{ background: colors.dot + '20', color: colors.dot }"
        >
          <IconTravel
            :name="typeIcon"
            :size="12"
            style="vertical-align:middle;margin-right:2px"
          /> {{ typeLabel }}
        </span>
        <div class="activity-item__name-group">
          <span class="activity-item__title">{{ activity.title }}</span>
          <span
            v-if="activity.subtitle"
            class="activity-item__subtitle"
          >{{ activity.subtitle }}</span>
        </div>
        <div class="activity-item__right">
          <span
            v-if="activity.duration_minutes"
            class="activity-item__duration"
          >
            {{ activity.duration_minutes }}分钟
          </span>
          <span
            v-if="activity.cost === 0"
            class="activity-item__cost activity-item__cost--free"
          >免费</span>
          <span
            v-else-if="activity.cost > 0"
            class="activity-item__cost"
          >¥{{ activity.cost }}</span>
        </div>
      </div>
      <div
        v-if="expanded"
        class="activity-item__detail"
      >
        <p class="activity-item__desc">
          {{ activity.description }}
        </p>
        <div class="activity-item__meta-row">
          <div
            v-if="activity.rating"
            class="activity-item__rating"
          >
            <svg
              width="14"
              height="14"
              viewBox="0 0 24 24"
              fill="#D4A857"
              stroke="#D4A857"
              stroke-width="1"
            >
              <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
            </svg>
            {{ activity.rating }}
          </div>
          <div
            v-if="activity.tags?.length"
            class="activity-item__tags"
          >
            <span
              v-for="tag in activity.tags"
              :key="tag"
              class="activity-item__tag"
            >{{ tag }}</span>
          </div>
        </div>
        <div
          v-if="activity.tips"
          class="activity-item__tips"
        >
          {{ activity.tips }}
        </div>
        <div class="activity-item__actions">
          <a-button
            size="small"
            @click.stop="emit('replace')"
          >
            <template #icon>
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              ><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" /><polyline points="17 8 12 3 7 8" /><line
                x1="12"
                y1="3"
                x2="12"
                y2="15"
              /></svg>
            </template>
            替换
          </a-button>
          <a-button
            size="small"
            danger
            @click.stop="emit('remove')"
          >
            <template #icon>
              <svg
                width="12"
                height="12"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
              ><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
            </template>
            删除
          </a-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
/*
 * 活动项布局：白色时间轴竖线（DayCard）在左 52px，
 * 青色圆点在其右侧（58px），内容从圆点右侧开始排列。
 * 右侧显示浏览时长和费用。
 */

.activity-item {
  position: relative;
  padding: var(--space-3) var(--space-4) var(--space-3) 12px;
  margin-left: 0;
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-in-out);
  border-radius: var(--radius-sm);
}
.activity-item:hover {
  background: var(--color-bg-secondary);
}

/* 青色竖线 — 白线右侧（via CSS 变量动态传色） */
.activity-item::before {
  content: '';
  position: absolute;
  left: 56px;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--cyan-color);
  border-radius: 2px;
}

.activity-item__dot {
  position: absolute;
  left: 53px;
  top: var(--space-4);
  width: 10px;
  height: 10px;
  border-radius: 50%;
  z-index: 1;
}

.activity-item__body {
  min-width: 0;
}

.activity-item__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.activity-item__time {
  font-size: var(--text-caption);
  font-weight: var(--fw-medium);
  color: var(--color-brand-700);
  white-space: nowrap;
  min-width: 46px;
  flex-shrink: 0;
  margin-left: 52px; /* 跳过时间轴区域 */
}

.activity-item__type-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: var(--radius-pill);
  white-space: nowrap;
  flex-shrink: 0;
  margin-left: 8px; /* 与时间字段的间距 */
}

.activity-item__name-group {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.activity-item__title {
  font-size: var(--text-body);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
  line-height: 1.3;
}

.activity-item__subtitle {
  font-size: var(--text-body-sm);
  color: var(--color-text-tertiary);
  line-height: 1.3;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.activity-item__right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  flex-shrink: 0;
  margin-left: auto;
}

.activity-item__duration {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
  white-space: nowrap;
  padding: 1px 6px;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
}

.activity-item__cost {
  font-size: var(--text-body-sm);
  font-weight: var(--fw-semibold);
  color: var(--color-brand-600);
  white-space: nowrap;
}

.activity-item__cost--free {
  color: var(--color-success, #3B6D11);
  font-size: var(--text-small);
}

.activity-item__detail {
  margin-top: var(--space-3);
  padding-left: 0;
  animation: fadeIn 0.2s ease;
}

.activity-item__desc {
  font-size: var(--text-body-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-2);
  line-height: 1.5;
}

.activity-item__meta-row {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
  flex-wrap: wrap;
}

.activity-item__rating {
  font-size: var(--text-small);
  color: var(--color-gold);
  display: flex;
  align-items: center;
  gap: 3px;
}

.activity-item__tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-1);
}

.activity-item__tag {
  font-size: 11px;
  padding: 1px 6px;
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
  border-radius: var(--radius-pill);
}

.activity-item__tips {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
  background: var(--color-brand-50);
  padding: var(--space-2) var(--space-3);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-3);
  border-left: 2px solid var(--color-brand-300);
}

.activity-item__actions {
  display: flex;
  gap: var(--space-2);
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(-4px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
