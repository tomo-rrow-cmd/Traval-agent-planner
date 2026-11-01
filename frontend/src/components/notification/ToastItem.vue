<script setup lang="ts">
/* ============================================================
   ToastItem — 单条通知
   对应文档：界面视觉设计系统.md · §10.1
   ============================================================ */

import type { Toast } from '@/store/uiStore'

const props = defineProps<{
  toast: Toast
}>()

const emit = defineEmits<{
  dismiss: []
}>()

const typeConfig: Record<string, { bg: string; border: string; icon: string }> = {
  success: { bg: 'var(--color-success)', border: 'var(--color-success)', icon: '✓' },
  error: { bg: 'var(--color-error)', border: 'var(--color-error)', icon: '✕' },
  warning: { bg: 'var(--color-warning)', border: 'var(--color-warning)', icon: '!' },
  info: { bg: 'var(--color-info)', border: 'var(--color-info)', icon: 'i' },
}

const config = typeConfig[props.toast.type] || typeConfig.info
</script>

<template>
  <div
    class="toast-item"
    :style="{ borderLeftColor: config.border }"
  >
    <div
      class="toast-item__icon"
      :style="{ background: config.bg }"
    >
      {{ config.icon }}
    </div>
    <div class="toast-item__body">
      <div class="toast-item__message">
        {{ toast.message }}
      </div>
      <div
        v-if="toast.description"
        class="toast-item__desc"
      >
        {{ toast.description }}
      </div>
      <button
        v-if="toast.action"
        class="toast-item__action"
        @click="toast.action!.handler()"
      >
        {{ toast.action.label }}
      </button>
    </div>
    <button
      class="toast-item__close"
      @click="emit('dismiss')"
    >
      ✕
    </button>
  </div>
</template>

<style scoped>
.toast-item {
  display: flex;
  align-items: flex-start;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  border-left: 4px solid;
  box-shadow: var(--shadow-toast);
  min-width: 300px;
  max-width: 400px;
}

.toast-item__icon {
  width: 24px;
  height: 24px;
  border-radius: var(--radius-full);
  color: white;
  font-size: 12px;
  font-weight: var(--fw-bold);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.toast-item__body {
  flex: 1;
  min-width: 0;
}

.toast-item__message {
  font-size: var(--text-body-sm);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
  line-height: 1.4;
}

.toast-item__desc {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
  margin-top: 2px;
}

.toast-item__action {
  margin-top: var(--space-2);
  padding: 0;
  border: none;
  background: none;
  color: var(--color-brand-500);
  font-size: var(--text-small);
  font-weight: var(--fw-medium);
  cursor: pointer;
}
.toast-item__action:hover {
  color: var(--color-brand-600);
  text-decoration: underline;
}

.toast-item__close {
  width: 20px;
  height: 20px;
  border: none;
  background: none;
  color: var(--color-text-tertiary);
  font-size: 12px;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  transition: all var(--dur-fast) var(--ease-in-out);
}
.toast-item__close:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}
</style>
