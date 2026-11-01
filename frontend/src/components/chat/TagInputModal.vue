<script setup lang="ts">
/* ============================================================
   TagInputModal — 自定义标签输入弹窗
   旅行手账风格，与 UI 设计系统一致
   ============================================================ */

import { ref, nextTick, computed } from 'vue'

const props = withDefaults(defineProps<{
  maxTags?: number
  currentCount?: number
}>(), {
  maxTags: 20,
  currentCount: 0,
})

const emit = defineEmits<{
  confirm: [value: string]
  close: []
}>()

const visible = defineModel<boolean>('visible', { default: false })

const tagValue = ref('')
const inputRef = ref<HTMLInputElement | null>(null)

const isFull = computed(() => props.currentCount >= props.maxTags)

function handleOpen() {
  visible.value = true
  tagValue.value = ''
  nextTick(() => inputRef.value?.focus())
}

function handleConfirm() {
  const trimmed = tagValue.value.trim()
  if (trimmed) {
    emit('confirm', trimmed)
  }
  visible.value = false
}

function handleClose() {
  visible.value = false
  emit('close')
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter') {
    e.preventDefault()
    handleConfirm()
  }
  if (e.key === 'Escape') {
    handleClose()
  }
}

defineExpose({ open: handleOpen })
</script>

<template>
  <Transition name="tag-modal">
    <div
      v-if="visible"
      class="tag-modal"
      @click.self="handleClose"
    >
      <div
        class="tag-modal__backdrop"
        @click="handleClose"
      />
      <div class="tag-modal__panel">
        <!-- 顶部色带 -->
        <div class="tag-modal__stripe" />

        <div class="tag-modal__body">
          <div class="tag-modal__header">
            <h3 class="tag-modal__title">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                stroke-width="2"
                stroke-linecap="round"
                style="color: var(--color-brand-500);"
              >
                <circle
                  cx="12"
                  cy="12"
                  r="10"
                /><line
                  x1="12"
                  y1="8"
                  x2="12"
                  y2="16"
                /><line
                  x1="8"
                  y1="12"
                  x2="16"
                  y2="12"
                />
              </svg>
              添加自定义标签
            </h3>
          </div>

          <p class="tag-modal__hint">
            输入你想添加到输入框的关键词
            <span class="tag-modal__count">{{ currentCount }}/{{ maxTags }}</span>
          </p>

          <div class="tag-modal__input-wrap">
            <input
              ref="inputRef"
              v-model="tagValue"
              class="tag-modal__input"
              type="text"
              placeholder="例如：预算5000"
              maxlength="30"
              :disabled="isFull"
              @keydown="handleKeydown"
            >
          </div>

          <div
            v-if="isFull"
            class="tag-modal__full-hint"
          >
            已达到标签数量上限（{{ maxTags }} 个）
          </div>

          <div class="tag-modal__actions">
            <button
              class="tag-modal__btn tag-modal__btn--cancel"
              @click="handleClose"
            >
              取消
            </button>
            <button
              class="tag-modal__btn tag-modal__btn--confirm"
              :disabled="!tagValue.trim() || isFull"
              @click="handleConfirm"
            >
              添加
            </button>
          </div>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.tag-modal {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
}

.tag-modal__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(44, 44, 44, 0.3);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

.tag-modal__panel {
  position: relative;
  width: 100%;
  max-width: 360px;
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: 0 16px 48px rgba(44, 44, 44, 0.18);
  overflow: hidden;
}

.tag-modal__stripe {
  height: 4px;
  background: var(--card-ribbon-bg);
}

.tag-modal__body {
  padding: var(--space-6);
}

.tag-modal__header {
  margin-bottom: var(--space-2);
}

.tag-modal__title {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-h4);
  font-weight: var(--fw-semibold);
  color: var(--color-text-primary);
  margin: 0;
}

.tag-modal__hint {
  font-size: var(--text-body-sm);
  color: var(--color-text-tertiary);
  margin: 0 0 var(--space-5);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.tag-modal__count {
  font-size: 11px;
  padding: 1px 8px;
  border-radius: 10px;
  background: var(--color-brand-50);
  color: var(--color-brand-600);
}

.tag-modal__full-hint {
  font-size: 12px;
  color: var(--color-warning);
  margin: -12px 0 14px;
  padding: 6px 10px;
  background: var(--color-brand-50);
  border-radius: 6px;
}

/* 输入框 */
.tag-modal__input-wrap {
  display: flex;
  align-items: center;
  height: 44px;
  border: 1.5px solid var(--input-border-color);
  border-radius: var(--input-radius);
  background: var(--color-bg-card);
  transition: all var(--dur-fast) var(--ease-in-out);
  margin-bottom: var(--space-5);
  overflow: hidden;
}
.tag-modal__input-wrap:focus-within {
  border-color: var(--color-brand-500);
  box-shadow: var(--input-focus-shadow);
}

.tag-modal__input {
  flex: 1;
  height: 100%;
  border: none;
  outline: none;
  padding: 0 var(--space-3);
  font-size: var(--text-body);
  color: var(--color-text-primary);
  background: transparent;
}
.tag-modal__input::placeholder {
  color: var(--color-text-placeholder);
}

/* 按钮区 */
.tag-modal__actions {
  display: flex;
  gap: var(--space-3);
}

.tag-modal__btn {
  flex: 1;
  height: 40px;
  border-radius: var(--radius-sm);
  font-size: var(--text-body);
  font-weight: var(--fw-medium);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-in-out);
  font-family: inherit;
}

.tag-modal__btn--cancel {
  border: 1.5px solid var(--color-border);
  background: transparent;
  color: var(--color-text-secondary);
}
.tag-modal__btn--cancel:hover {
  border-color: var(--color-brand-300);
  color: var(--color-brand-600);
  background: var(--color-brand-50);
}

.tag-modal__btn--confirm {
  border: none;
  background: var(--color-brand-500);
  color: #fff;
  box-shadow: var(--btn-primary-shadow);
}
.tag-modal__btn--confirm:hover:not(:disabled) {
  background: var(--color-brand-600);
  box-shadow: var(--btn-primary-shadow-hover);
}
.tag-modal__btn--confirm:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

/* ===== 过渡动画 ===== */
.tag-modal-enter-active {
  transition: opacity 0.3s var(--ease-out-expo);
}
.tag-modal-leave-active {
  transition: opacity 0.2s var(--ease-in-out);
}
.tag-modal-enter-active .tag-modal__panel {
  animation: panelPop 0.3s var(--ease-out-expo);
}
.tag-modal-leave-active .tag-modal__panel {
  animation: panelShrink 0.2s var(--ease-in-out) forwards;
}
.tag-modal-enter-from,
.tag-modal-leave-to {
  opacity: 0;
}

@keyframes panelPop {
  from {
    opacity: 0;
    transform: translateY(16px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes panelShrink {
  from {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
  to {
    opacity: 0;
    transform: translateY(8px) scale(0.95);
  }
}

/* ===== 深色模式 ===== */
[data-theme="dark"] .tag-modal__backdrop {
  background: rgba(0, 0, 0, 0.6);
}

[data-theme="dark"] .tag-modal__panel {
  background: var(--color-bg-card);
  box-shadow: 0 16px 48px rgba(0, 0, 0, 0.4);
}

[data-theme="dark"] .tag-modal__btn--cancel {
  border-color: var(--color-border);
  color: var(--color-text-secondary);
}
[data-theme="dark"] .tag-modal__btn--cancel:hover {
  border-color: var(--color-brand-300);
  color: var(--color-brand-400);
  background: var(--color-brand-50);
}

[data-theme="dark"] .tag-modal__count {
  background: var(--color-brand-100);
}

[data-theme="dark"] .tag-modal__full-hint {
  background: var(--color-brand-50);
}
</style>
