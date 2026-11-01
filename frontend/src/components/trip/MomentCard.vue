<script setup lang="ts">
/**
 * MomentCard — 朋友圈预览卡片
 */
import type { SocialMaterial } from '@/api/travelogue'
import PhotoGrid from './PhotoGrid.vue'

defineProps<{
  material: SocialMaterial
}>()

const emit = defineEmits<{
  favorite: [id: string, isFavorite: boolean]
}>()
</script>

<template>
  <div class="moment-card">
    <div class="moment-header">
      <div class="avatar">
        👤
      </div>
      <div class="user-info">
        <span class="user-name">旅行者</span>
        <span
          v-if="material.location_tag"
          class="location"
        >
          📍 {{ material.location_tag }}
        </span>
      </div>
    </div>

    <p
      v-if="material.title"
      class="moment-text"
    >
      {{ material.title }}
    </p>

    <PhotoGrid
      v-if="material.images?.length"
      :images="material.images"
      :layout="material.layout ?? 'grid_9'"
    />

    <div
      v-if="material.overlay_data"
      class="data-overlay"
    >
      <div
        v-for="(v, k) in material.overlay_data"
        :key="k"
        class="overlay-item"
      >
        <span class="overlay-value">{{ v }}</span>
        <span class="overlay-key">{{ k }}</span>
      </div>
    </div>

    <div
      v-if="material.hashtags?.length"
      class="hashtags"
    >
      <span
        v-for="tag in material.hashtags"
        :key="tag"
        class="tag"
      >{{ tag }}</span>
    </div>

    <div class="moment-actions">
      <button
        :class="['fav-btn', { active: material.is_favorite }]"
        @click="emit('favorite', material.id, !material.is_favorite)"
      >
        {{ material.is_favorite ? '❤️' : '🤍' }}
      </button>
    </div>
  </div>
</template>

<style scoped>
.moment-card {
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  padding: 16px;
  box-shadow: var(--shadow-float);
}

.moment-header {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--color-bg-tertiary);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}

.user-name {
  font-weight: 600;
  font-size: 14px;
  color: var(--color-text-primary);
}

.location {
  display: block;
  font-size: 11px;
  color: var(--color-text-tertiary);
}

.moment-text {
  font-size: 14px;
  line-height: 1.6;
  margin: 0 0 10px;
  white-space: pre-wrap;
  color: var(--color-text-primary);
}

.data-overlay {
  display: flex;
  gap: 12px;
  padding: 8px 0;
  margin: 8px 0;
  border-top: 1px solid var(--color-border-light);
  border-bottom: 1px solid var(--color-border-light);
}

.overlay-item { text-align: center; flex: 1; }

.overlay-value {
  display: block;
  font-size: 16px;
  font-weight: 700;
  color: var(--color-type-transport);
}

.overlay-key {
  display: block;
  font-size: 10px;
  color: var(--color-text-tertiary);
  text-transform: capitalize;
}

.hashtags {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  margin-top: 8px;
}

.tag {
  color: var(--color-type-transport);
  font-size: 12px;
}

.moment-actions {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px solid var(--color-border-light);
}

.fav-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 18px;
  padding: 2px 6px;
}

.fav-btn.active { animation: pulse 0.3s ease; }

@keyframes pulse {
  0% { transform: scale(1); }
  50% { transform: scale(1.2); }
  100% { transform: scale(1); }
}
</style>
