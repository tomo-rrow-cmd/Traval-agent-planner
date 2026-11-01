<script setup lang="ts">
/**
 * PhotoGrid — 9宫格照片展示组件
 *
 * 支持 grid_9 / grid_4 / single 布局
 * 点击图片可放大查看
 */
import { ref } from 'vue'

export interface GridImage {
  url: string
  caption?: string
  order: number
  is_cover?: boolean
}

const props = defineProps<{
  images: GridImage[]
  layout?: string  // grid_9 | grid_4 | single_v | single_h | card
}>()

const previewIndex = ref<number | null>(null)

function gridClass(): string {
  const map: Record<string, string> = {
    grid_9: 'grid-9',
    grid_4: 'grid-4',
    single_v: 'single-v',
    single_h: 'single-h',
    card: 'card-layout',
  }
  return map[props.layout ?? 'grid_9'] ?? 'grid-9'
}

function openPreview(index: number) {
  previewIndex.value = index
}

function closePreview() {
  previewIndex.value = null
}
</script>

<template>
  <div
    v-if="images.length > 0"
    :class="['photo-grid', gridClass()]"
  >
    <div
      v-for="(img, index) in images.slice(0, layout === 'grid_9' ? 9 : 12)"
      :key="index"
      :class="['grid-cell', { cover: img.is_cover }]"
      @click="openPreview(index)"
    >
      <img
        :src="img.url"
        :alt="img.caption ?? ''"
        loading="lazy"
      >
      <span
        v-if="img.caption"
        class="caption"
      >{{ img.caption }}</span>
    </div>

    <!-- Preview modal -->
    <Teleport to="body">
      <div
        v-if="previewIndex !== null"
        class="preview-overlay"
        @click="closePreview"
      >
        <img
          :src="images[previewIndex]?.url"
          :alt="images[previewIndex]?.caption ?? ''"
          class="preview-img"
        >
        <p
          v-if="images[previewIndex]?.caption"
          class="preview-caption"
        >
          {{ images[previewIndex]?.caption }}
        </p>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.photo-grid {
  display: grid;
  gap: 4px;
}

.grid-9 {
  grid-template-columns: repeat(3, 1fr);
  aspect-ratio: 1;
}

.grid-4 {
  grid-template-columns: repeat(2, 1fr);
}

.single-v {
  grid-template-columns: 1fr;
}

.single-h {
  grid-template-columns: 1fr;
}

.card-layout {
  grid-template-columns: repeat(4, 1fr);
}

.grid-cell {
  position: relative;
  overflow: hidden;
  border-radius: 4px;
  cursor: pointer;
  background: var(--color-bg-tertiary);
}

.grid-cell img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.grid-cell.cover {
  grid-row: span 2;
  grid-column: span 2;
}

.caption {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  padding: 4px 8px;
  background: linear-gradient(transparent, rgba(0,0,0,0.6));
  color: #fff;
  font-size: 12px;
}

.preview-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0,0,0,0.9);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  cursor: pointer;
}

.preview-img {
  max-width: 90vw;
  max-height: 80vh;
  object-fit: contain;
  border-radius: 8px;
}

.preview-caption {
  color: #fff;
  margin-top: 16px;
  font-size: 14px;
}
</style>
