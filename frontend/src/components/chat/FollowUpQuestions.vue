<script setup lang="ts">
/* ============================================================
   FollowUpQuestions — AI 追问卡片（杂志风格）
   设计灵感：小地球旅行的诗意质感
   ============================================================ */

import { computed } from 'vue'

const props = defineProps<{
  question: string
  suggestions?: string[]
}>()

const emit = defineEmits<{
  answer: [value: string]
}>()

// 为选项增加 emoji
const optionEmoji: Record<string, string> = {
  '北京': '🏙️', '上海': '🌆', '广州': '🌇', '成都': '🐼',
  '大理': '🌊', '丽江': '🏔️', '三亚': '🏖️', '杭州': '🏞️',
  '西安': '🏛️', '重庆': '🌶️', '厦门': '🌅', '深圳': '🌃',
  '1人': '🚶', '2人': '👫', '3人': '👨‍👩‍👧', '4人': '👨‍👩‍👧‍👦',
  '5人以上': '👨‍👩‍👧‍👧', '情侣': '💑', '家庭': '👨‍👩‍👧‍👦', '朋友': '👬',
  '休闲': '😌', '紧凑': '🏃', '美食': '🍜', '文化': '🏛️',
}

const items = computed(() =>
  (props.suggestions || []).map((s) => ({
    text: s,
    emoji: Object.entries(optionEmoji).find(([key]) => s.includes(key))?.[1] || '💡',
  }))
)
</script>

<template>
  <div class="follow-up">
    <!-- 追问卡片 — 手账风格 -->
    <div class="follow-up__card">
      <div class="follow-up__card-stripe" />
      <div class="follow-up__card-body">
        <div class="follow-up__header">
          <span class="follow-up__icon">🤔</span>
          <span class="follow-up__label">AI 想知道</span>
        </div>
        <p class="follow-up__question">
          {{ question }}
        </p>
      </div>
    </div>

    <!-- 选项按钮 — 卡片风格 -->
    <div
      v-if="items.length > 0"
      class="follow-up__options"
    >
      <button
        v-for="item in items"
        :key="item.text"
        class="follow-up__chip"
        @click="emit('answer', item.text)"
      >
        <span class="follow-up__chip-emoji">{{ item.emoji }}</span>
        <span class="follow-up__chip-text">{{ item.text }}</span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.follow-up {
  margin: var(--space-4) 0 var(--space-3);
  animation: cardPop 0.35s var(--ease-spring);
}

@keyframes cardPop {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}

/* 追问卡片 */
.follow-up__card {
  position: relative;
  max-width: 520px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-brand-200);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 20px rgba(232, 168, 124, 0.08);
}

.follow-up__card-stripe {
  height: 3px;
  background: var(--gradient-gold);
}

.follow-up__card-body {
  padding: var(--space-4) var(--space-5);
}

.follow-up__header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}

.follow-up__icon {
  font-size: 18px;
  line-height: 1;
}

.follow-up__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--color-brand-500);
  letter-spacing: 1px;
  text-transform: uppercase;
}

.follow-up__question {
  font-size: var(--text-body);
  color: var(--color-text-primary);
  line-height: 1.7;
  margin: 0;
  font-weight: 450;
}

/* 选项按钮 */
.follow-up__options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
  margin-top: var(--space-3);
  padding-left: var(--space-4);
}

.follow-up__chip {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: 8px 18px;
  border: 1.5px solid var(--color-brand-200);
  border-radius: 12px;
  background: var(--color-bg-card);
  cursor: pointer;
  transition: all 0.25s var(--ease-spring);
  font-family: inherit;
  box-shadow: 0 2px 8px rgba(139, 115, 85, 0.04);
}

.follow-up__chip:hover {
  border-color: var(--color-brand-400);
  background: var(--color-brand-50);
  transform: translateY(-2px) scale(1.02);
  box-shadow: 0 4px 16px rgba(232, 168, 124, 0.12);
}

.follow-up__chip:active {
  transform: translateY(0) scale(1);
}

.follow-up__chip-emoji {
  font-size: 15px;
  line-height: 1;
}

.follow-up__chip-text {
  font-size: 14px;
  font-weight: 500;
  color: var(--color-brand-700);
  white-space: nowrap;
}
</style>
