<script setup lang="ts">
/* ============================================================
   PlanCard — 方案摘要卡片（杂志封面风格）
   图片区放大 + 艺术字占位 + 收藏动效
   ============================================================ */

import type { PlanSummary } from '@/types/plan'

defineProps<{
  plan: PlanSummary
}>()

const emit = defineEmits<{
  click: []
  favorite: []
}>()

const styleLabels: Record<string, string> = {
  relaxed: '休闲',
  balanced: '均衡',
  intensive: '紧凑',
  food: '美食',
  culture: '文化',
  adventure: '探险',
}
</script>

<template>
  <div
    class="plan-card"
    @click="emit('click')"
  >
    <!-- 图片区：杂志封面风格 -->
    <div class="plan-card__image">
      <div class="plan-card__image-placeholder">
        <span class="plan-card__image-letter">{{ plan.destination?.charAt(0) || '旅' }}</span>
      </div>
      <!-- 渐变遮罩 -->
      <div class="plan-card__image-overlay" />
      <!-- 天数徽章 -->
      <div class="plan-card__badge">
        {{ plan.days }}天
      </div>
      <!-- 收藏按钮 -->
      <button
        class="plan-card__favorite"
        :class="{ 'plan-card__favorite--active': plan.is_favorite }"
        :title="plan.is_favorite ? '取消收藏' : '收藏'"
        @click.stop="emit('favorite')"
      >
        <svg
          :fill="plan.is_favorite ? '#E8A87C' : 'none'"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          stroke="#E8A87C"
          stroke-width="2"
          class="plan-card__star"
        >
          <polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2" />
        </svg>
      </button>
    </div>

    <!-- 卡片正文 -->
    <div class="plan-card__body">
      <h3 class="plan-card__title">
        {{ plan.title }}
      </h3>
      <div class="plan-card__meta">
        <span class="plan-card__destination">{{ plan.destination }}</span>
        <span class="plan-card__dot">·</span>
        <span class="plan-card__date">{{ plan.start_date }} ~ {{ plan.end_date }}</span>
      </div>
      <div class="plan-card__footer">
        <span
          v-if="plan.travel_style"
          class="plan-card__style"
        >
          {{ styleLabels[plan.travel_style] || plan.travel_style }}
        </span>
        <span class="plan-card__cost">¥{{ plan.estimated_cost?.toFixed(0) }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.plan-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.4s var(--ease-out-expo);
}
.plan-card:hover {
  box-shadow: var(--shadow-card-hover);
  transform: translateY(-4px);
}

/* ===== 图片区（180px，杂志封面风格） ===== */
.plan-card__image {
  position: relative;
  height: 140px;
  overflow: hidden;
}

.plan-card__image-placeholder {
  width: 100%;
  height: 100%;
  background: linear-gradient(145deg, var(--color-brand-200), var(--color-brand-500));
  display: flex;
  align-items: center;
  justify-content: center;
}

.plan-card__image-letter {
  font-size: 56px;
  font-weight: 800;
  color: rgba(255, 255, 255, 0.35);
  line-height: 1;
  user-select: none;
  transition: transform 0.6s var(--ease-out-expo);
}
.plan-card:hover .plan-card__image-letter {
  transform: scale(1.12);
}

.plan-card__image-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 50%, rgba(0,0,0,0.25) 100%);
  pointer-events: none;
}

/* ===== 天数徽章 ===== */
.plan-card__badge {
  position: absolute;
  top: var(--space-3);
  left: var(--space-3);
  padding: 3px 12px;
  background: rgba(0, 0, 0, 0.45);
  color: white;
  font-size: var(--text-small);
  font-weight: var(--fw-semibold);
  border-radius: var(--radius-pill);
  backdrop-filter: blur(4px);
}

/* ===== 收藏按钮 ===== */
.plan-card__favorite {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  width: 34px;
  height: 34px;
  border: none;
  background: rgba(255, 255, 255, 0.85);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  backdrop-filter: blur(6px);
  transition: all 0.25s var(--ease-out-expo);
}
.plan-card__favorite:hover {
  background: white;
  transform: scale(1.15);
}
.plan-card__favorite:active .plan-card__star {
  animation: heartBeat 0.4s var(--ease-spring);
}

@keyframes heartBeat {
  0%   { transform: scale(1); }
  40%  { transform: scale(1.35); }
  70%  { transform: scale(0.9); }
  100% { transform: scale(1); }
}

/* ===== 正文区 ===== */
.plan-card__body {
  padding: var(--space-3) var(--space-4) var(--space-4);
}

.plan-card__title {
  font-size: var(--text-body-lg);
  font-weight: var(--fw-semibold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.plan-card__meta {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: var(--text-body-sm);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-4);
}

.plan-card__destination {
  color: var(--color-text-secondary);
  font-weight: var(--fw-medium);
}

.plan-card__dot {
  color: var(--color-border);
}

.plan-card__footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.plan-card__style {
  font-size: var(--text-small);
  padding: 2px 10px;
  background: var(--color-brand-50);
  color: var(--color-brand-700);
  border-radius: var(--radius-pill);
  font-weight: var(--fw-medium);
}

.plan-card__cost {
  font-size: var(--text-body);
  font-weight: var(--fw-bold);
  color: var(--color-brand-600);
}
</style>
