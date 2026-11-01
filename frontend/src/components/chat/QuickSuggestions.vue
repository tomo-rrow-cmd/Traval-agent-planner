<script setup lang="ts">
/* ============================================================
   QuickSuggestions — 卡片式快捷建议
   设计灵感：Wonderplan 的视觉化选择卡片
   ============================================================ */

import { computed } from 'vue'

const props = withDefaults(defineProps<{
  suggestions: string[]
  maxTags?: number
}>(), {
  maxTags: 20,
})

const emit = defineEmits<{
  addTag: [value: string]
  addCustom: []
  removeTag: [value: string]
}>()

// emoji 映射（按关键词）
const suggestEmoji: Record<string, string> = {
  '北京': '🏙️', '上海': '🌆', '广州': '🌇', '深圳': '🌃',
  '成都': '🐼', '重庆': '🌶️', '杭州': '🏞️', '西安': '🏛️',
  '大理': '🌊', '丽江': '🏔️', '三亚': '🏖️', '厦门': '🌅',
  '3天': '📅', '5天': '📅', '7天': '📅',
  '休闲': '😌', '紧凑': '🏃', '美食': '🍜', '文化': '🏛️',
  '放松': '🧘', '探险': '🧗', '浪漫': '💕', '亲子': '👨‍👩‍👧‍👦',
}

const items = computed(() =>
  props.suggestions.map((s) => ({
    text: s,
    emoji: Object.entries(suggestEmoji).find(([key]) => s.includes(key))?.[1] || '📍',
  }))
)

const canAddMore = computed(() => props.suggestions.length < props.maxTags)
</script>

<template>
  <div
    v-if="suggestions.length > 0"
    class="quick-suggestions"
  >
    <div class="quick-suggestions__label">
      <span class="quick-suggestions__label-dot" />
      快捷选择
    </div>
    <div class="quick-suggestions__grid">
      <button
        v-for="item in items"
        :key="item.text"
        class="quick-suggestions__card"
        @click="emit('addTag', item.text)"
      >
        <span class="quick-suggestions__emoji">{{ item.emoji }}</span>
        <span class="quick-suggestions__text">{{ item.text }}</span>
      </button>

      <!-- 自定义按钮 -->
      <button
        v-if="canAddMore"
        class="quick-suggestions__card quick-suggestions__card--custom"
        @click="emit('addCustom')"
      >
        <span class="quick-suggestions__custom-icon">+</span>
        <span class="quick-suggestions__text">自定义</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.quick-suggestions {
  margin: var(--space-3) 0;
  animation: slideUp 0.3s var(--ease-out-expo);
}

@keyframes slideUp {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.quick-suggestions__label {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: 11px;
  font-weight: 600;
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-2);
  letter-spacing: 0.5px;
  text-transform: uppercase;
}

.quick-suggestions__label-dot {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: var(--color-brand-300);
}

.quick-suggestions__grid {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.quick-suggestions__card {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 4px 10px;
  background: var(--color-bg-card);
  border: 1.5px solid var(--color-brand-200);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.25s var(--ease-spring);
  font-family: inherit;
  box-shadow: 0 2px 8px rgba(139, 115, 85, 0.04);
}

.quick-suggestions__card:hover {
  border-color: var(--color-brand-400);
  background: var(--color-brand-50);
  transform: translateY(-1px);
  box-shadow: 0 4px 16px rgba(232, 168, 124, 0.12);
}

.quick-suggestions__card:active {
  transform: translateY(0);
  transition-duration: 0.05s;
}

.quick-suggestions__card--custom {
  border-style: dashed;
  border-color: var(--color-brand-300);
  color: var(--color-brand-600);
}
.quick-suggestions__card--custom:hover {
  background: var(--color-brand-50);
  border-color: var(--color-brand-500);
}

.quick-suggestions__custom-icon {
  font-size: 13px;
  font-weight: 700;
  line-height: 1;
}

.quick-suggestions__emoji {
  font-size: 14px;
  line-height: 1;
}

.quick-suggestions__text {
  font-size: 12px;
  font-weight: 500;
  color: var(--color-brand-700);
  white-space: nowrap;
}
</style>
