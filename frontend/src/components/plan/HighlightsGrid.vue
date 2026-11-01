<script setup lang="ts">
/* ============================================================
   HighlightsGrid — 行程亮点 + 概览数据统计
   渲染 PlanDetail.overview 中的 highlights、total_distance_km、transport_modes
   同时显示 crowd_type 和 people_count 等概览信息
   ============================================================ */

import { computed } from 'vue'

const props = defineProps<{
  highlights: string[]
  totalDistanceKm?: number
  transportModes?: string[]
  crowdType?: string
  peopleCount?: number
}>()

const hasData = computed(() => {
  return (
    props.highlights.length > 0 ||
    props.totalDistanceKm ||
    (props.transportModes && props.transportModes.length > 0) ||
    props.crowdType
  )
})

/** 交通方式图标映射（兼容中英文） */
const MODE_EMOJI: Record<string, string> = {
  walking: '🚶',步行: '🚶',
  transit: '🚌',公交: '🚌',巴士: '🚌',
  driving: '🚗',自驾: '🚗',开车: '🚗',
  taxi: '🚕',打车: '🚕',出租车: '🚕',
  subway: '🚇',地铁: '🚇',
  bus: '🚌',大巴: '🚌',
  bike: '🚲',骑行: '🚲',自行车: '🚲',
  flight: '✈️',飞机: '✈️',
  train: '🚄',高铁: '🚄',火车: '🚄',动车: '🚄',
}

function modeToEmoji(mode: string): string {
  return MODE_EMOJI[mode] || mode
}
</script>

<template>
  <div
    v-if="hasData"
    class="highlights-grid"
  >
    <!-- 概览统计条 -->
    <div
      v-if="totalDistanceKm || (transportModes && transportModes.length) || crowdType"
      class="highlights-grid__stats"
    >
      <div
        v-if="totalDistanceKm"
        class="highlights-grid__stat"
      >
        <span class="highlights-grid__stat-icon">📏</span>
        <span class="highlights-grid__stat-value">{{ (totalDistanceKm ?? 0).toFixed(0) }} km</span>
        <span class="highlights-grid__stat-label">总行程</span>
      </div>
      <div
        v-if="transportModes && transportModes.length"
        class="highlights-grid__stat"
      >
        <span class="highlights-grid__stat-icon">🚌</span>
        <span class="highlights-grid__stat-value">
          {{ transportModes.map(m => modeToEmoji(m)).join(' ') }}
        </span>
        <span class="highlights-grid__stat-label">交通方式</span>
      </div>
      <div
        v-if="crowdType"
        class="highlights-grid__stat"
      >
        <span class="highlights-grid__stat-icon">👥</span>
        <span class="highlights-grid__stat-value">{{ crowdType }}</span>
        <span class="highlights-grid__stat-label">适合人群</span>
      </div>
    </div>

    <!-- 亮点卡片 -->
    <div
      v-if="highlights.length"
      class="highlights-grid__items"
    >
      <div
        v-for="(item, i) in highlights"
        :key="i"
        class="highlights-grid__card"
      >
        <div class="highlights-grid__card-icon">
          ✨
        </div>
        <div class="highlights-grid__card-text">
          {{ item }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.highlights-grid {
  margin: 16px 0;
}

/* ---- 统计条 ---- */
.highlights-grid__stats {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 16px;
}

.highlights-grid__stat {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  border-radius: 10px;
  flex: 1;
  min-width: 120px;
}

.highlights-grid__stat-icon {
  font-size: 18px;
  line-height: 1;
}

.highlights-grid__stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.highlights-grid__stat-label {
  font-size: 11px;
  color: var(--color-text-tertiary);
  margin-left: auto;
}

/* ---- 亮点卡片 ---- */
.highlights-grid__items {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 10px;
}

.highlights-grid__card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 12px 14px;
  border-radius: 10px;
  background: var(--color-brand-50);
  border: 1px solid var(--color-brand-100);
}

.highlights-grid__card-icon {
  font-size: 18px;
  flex-shrink: 0;
  line-height: 1.4;
}

.highlights-grid__card-text {
  font-size: 13px;
  line-height: 1.5;
  color: var(--color-text-secondary);
}
</style>
