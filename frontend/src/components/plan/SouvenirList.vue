<script setup lang="ts">
/* ============================================================
   SouvenirList — 纪念品推荐列表
   渲染 PlanDetail.souvenir_recommendations 字段
   ============================================================ */

import type { SouvenirRecommendation } from '@/types/plan'

defineProps<{
  items: SouvenirRecommendation[]
}>()
</script>

<template>
  <div
    v-if="items.length"
    class="souvenir-list"
  >
    <h3 class="block-section-title">
      <span class="souvenir-list__title-icon">🎁</span>
      纪念品推荐
    </h3>
    <div class="souvenir-list__grid">
      <div
        v-for="(item, i) in items"
        :key="i"
        class="souvenir-list__card"
      >
        <div class="souvenir-list__card-header">
          <span class="souvenir-list__name">{{ item.name }}</span>
          <span class="souvenir-list__price">{{ item.estimated_price }}</span>
        </div>
        <p
          v-if="item.description"
          class="souvenir-list__desc"
        >
          {{ item.description }}
        </p>
        <div
          v-if="item.buy_place"
          class="souvenir-list__buy-place"
        >
          <span class="souvenir-list__buy-icon">📍</span>
          {{ item.buy_place }}
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.souvenir-list {
  margin: 24px 0;
}

.block-section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 12px;
  color: var(--color-text-primary);
  display: flex;
  align-items: center;
  gap: 6px;
}

.souvenir-list__title-icon {
  font-size: 18px;
  line-height: 1;
}

.souvenir-list__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 10px;
}

.souvenir-list__card {
  padding: 14px 16px;
  border-radius: 10px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border-light);
  transition: box-shadow var(--dur-fast);
}
.souvenir-list__card:hover {
  box-shadow: var(--shadow-float);
}

.souvenir-list__card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 6px;
}

.souvenir-list__name {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
}

.souvenir-list__price {
  font-size: 13px;
  font-weight: 500;
  color: var(--color-brand-600);
  white-space: nowrap;
  padding: 1px 8px;
  background: var(--color-brand-50);
  border-radius: 999px;
}

.souvenir-list__desc {
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.5;
  margin: 0 0 8px;
}

.souvenir-list__buy-place {
  font-size: 12px;
  color: var(--color-text-tertiary);
  display: flex;
  align-items: center;
  gap: 4px;
}

.souvenir-list__buy-icon {
  font-size: 12px;
  line-height: 1;
}
</style>
