<script setup lang="ts">
/* ============================================================
   ToastContainer — 全局通知容器
   对应文档：前端界面设计文档.md · §10
   ============================================================ */

import { useUiStore } from '@/store/uiStore'
import ToastItem from './ToastItem.vue'

const uiStore = useUiStore()
</script>

<template>
  <div class="toast-container">
    <TransitionGroup name="toast">
      <ToastItem
        v-for="toast in uiStore.toasts"
        :key="toast.id"
        :toast="toast"
        @dismiss="uiStore.dismissToast(toast.id)"
      />
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: var(--space-4);
  right: var(--space-4);
  z-index: var(--z-toast);
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
  max-width: 400px;
  pointer-events: none;
}
.toast-container > * {
  pointer-events: auto;
}

.toast-enter-active {
  transition: all 0.3s var(--ease-out-expo);
}
.toast-leave-active {
  transition: all 0.2s var(--ease-in-out);
}
.toast-enter-from {
  opacity: 0;
  transform: translateX(100%);
}
.toast-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
