<script setup lang="ts">
/* ============================================================
   InlineAlert — 内联提示条
   对应文档：前端界面设计文档.md · §10
   ============================================================ */

withDefaults(defineProps<{
  type?: 'success' | 'warning' | 'error' | 'info'
  message: string
  closable?: boolean
}>(), {
  type: 'info',
  closable: false,
})

const emit = defineEmits<{
  close: []
}>()

const typeStyles: Record<string, { bg: string; border: string; color: string }> = {
  success: { bg: 'rgba(91, 185, 138, 0.08)', border: 'var(--color-success)', color: 'var(--color-success)' },
  warning: { bg: 'rgba(232, 168, 55, 0.08)', border: 'var(--color-warning)', color: 'var(--color-warning)' },
  error: { bg: 'rgba(217, 96, 92, 0.08)', border: 'var(--color-error)', color: 'var(--color-error)' },
  info: { bg: 'rgba(126, 184, 218, 0.08)', border: 'var(--color-info)', color: 'var(--color-info)' },
}
</script>

<template>
  <div
    class="inline-alert"
    :style="{
      background: typeStyles[type].bg,
      borderLeftColor: typeStyles[type].border,
    }"
  >
    <span
      class="inline-alert__msg"
      :style="{ color: typeStyles[type].color }"
    >
      {{ message }}
    </span>
    <button
      v-if="closable"
      class="inline-alert__close"
      @click="emit('close')"
    >
      ✕
    </button>
  </div>
</template>

<style scoped>
.inline-alert {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  border-left: 3px solid;
  border-radius: var(--radius-sm);
  font-size: var(--text-body-sm);
}

.inline-alert__msg {
  flex: 1;
  font-weight: var(--fw-medium);
}

.inline-alert__close {
  width: 18px;
  height: 18px;
  border: none;
  background: none;
  font-size: 11px;
  cursor: pointer;
  opacity: 0.5;
  transition: opacity var(--dur-fast);
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.inline-alert__close:hover {
  opacity: 1;
}
</style>
