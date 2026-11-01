<script setup lang="ts">
/**
 * ProgressBar — 行程进度条组件
 *
 * 环形进度 + 打卡数统计
 */
defineProps<{
  percent: number
  checked: number
  total: number
}>()
</script>

<template>
  <div class="progress-section">
    <div class="progress-ring">
      <svg
        viewBox="0 0 100 100"
        class="ring-svg"
      >
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          class="ring-bg"
          stroke-width="8"
        />
        <circle
          cx="50"
          cy="50"
          r="42"
          fill="none"
          stroke="url(#progressGradient)"
          stroke-width="8"
          stroke-linecap="round"
          :stroke-dasharray="264"
          :stroke-dashoffset="264 - (264 * percent) / 100"
          transform="rotate(-90 50 50)"
          class="ring-progress"
        />
        <defs>
          <linearGradient
            id="progressGradient"
            x1="0%"
            y1="0%"
            x2="100%"
            y2="0%"
          >
            <stop
              offset="0%"
              stop-color="var(--color-type-transport)"
            />
            <stop
              offset="100%"
              stop-color="var(--color-type-attraction)"
            />
          </linearGradient>
        </defs>
      </svg>
      <div class="ring-text">
        <span class="percent">{{ Math.round(percent) }}%</span>
        <span class="label">完成度</span>
      </div>
    </div>

    <div class="progress-stats">
      <div class="stat">
        <span class="stat-num">{{ checked }}</span>
        <span class="stat-label">已打卡</span>
      </div>
      <div class="stat-divider">
        /
      </div>
      <div class="stat">
        <span class="stat-num">{{ total }}</span>
        <span class="stat-label">总目标</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.progress-section {
  display: flex;
  align-items: center;
  gap: 24px;
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  padding: 16px 24px;
  margin-bottom: 20px;
}

.progress-ring {
  position: relative;
  width: 80px;
  height: 80px;
}

.ring-svg { width: 100%; height: 100%; }

.ring-bg { stroke: var(--color-bg-tertiary); }

.ring-progress { transition: stroke-dashoffset 0.6s ease; }

.ring-text {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
}

.percent {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-type-transport);
}

.ring-text .label {
  font-size: 10px;
  color: var(--color-text-tertiary);
}

.progress-stats {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stat { text-align: center; }

.stat-num {
  display: block;
  font-size: 22px;
  font-weight: 700;
  color: var(--color-text-primary);
}

.stat-label {
  display: block;
  font-size: 12px;
  color: var(--color-text-tertiary);
}

.stat-divider {
  color: var(--color-border);
  font-size: 20px;
}
</style>
