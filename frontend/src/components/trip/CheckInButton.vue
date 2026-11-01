<script setup lang="ts">
/**
 * CheckInButton — 签到按钮组件
 *
 * 含位置验证提示、快速签到动画
 */
import { ref } from 'vue'

const props = defineProps<{
  poiType: string
  poiName: string
  disabled?: boolean
}>()

const emit = defineEmits<{
  checkin: [{ type: string; name: string }]
}>()

const isAnimating = ref(false)

function handleClick() {
  if (props.disabled) return
  isAnimating.value = true
  emit('checkin', { type: props.poiType, name: props.poiName })
  setTimeout(() => (isAnimating.value = false), 1500)
}

function getLabel(): string {
  if (props.poiType === 'attraction') return '到达景点'
  if (props.poiType === 'restaurant' || props.poiType === 'food') return '到达餐厅'
  if (props.poiType === 'hotel') return '到达酒店'
  return '签到'
}
</script>

<template>
  <button
    :class="['checkin-btn', { animating: isAnimating, disabled }]"
    :disabled="disabled"
    @click="handleClick"
  >
    <span
      v-if="!isAnimating"
      class="btn-content"
    >
      <span class="icon">📍</span>
      {{ getLabel() }}
    </span>
    <span
      v-else
      class="btn-content"
    >
      <span class="icon">✅</span>
      已签到！
    </span>
  </button>
</template>

<style scoped>
.checkin-btn {
  display: inline-flex;
  align-items: center;
  padding: 10px 24px;
  border-radius: var(--radius-pill);
  border: none;
  background: var(--gradient-ocean);
  color: #fff;
  font-size: 15px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.checkin-btn:hover:not(.disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(90, 158, 196, 0.4);
}

.checkin-btn.animating {
  background: var(--gradient-forest);
}

.checkin-btn.disabled {
  background: var(--color-bg-tertiary);
  color: var(--color-text-tertiary);
  cursor: not-allowed;
}

.btn-content {
  display: flex;
  align-items: center;
  gap: 6px;
}

.icon {
  font-size: 16px;
}

[data-theme="dark"] .checkin-btn {
  background: var(--gradient-ocean);
}
[data-theme="dark"] .checkin-btn.animating {
  background: var(--gradient-forest);
}
[data-theme="dark"] .checkin-btn:hover:not(.disabled) {
  box-shadow: 0 4px 12px rgba(74, 154, 130, 0.4);
}
</style>
