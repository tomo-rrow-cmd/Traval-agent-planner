<script setup lang="ts">
/* ============================================================
   ErrorBoundary — 错误边界
   ============================================================ */

import { ref } from 'vue'

const hasError = ref(false)
const errorMessage = ref('')

defineExpose({
  resetError() {
    hasError.value = false
    errorMessage.value = ''
  },
})

function handleRetry() {
  hasError.value = false
  errorMessage.value = ''
}
</script>

<template>
  <div
    v-if="hasError"
    class="error-boundary"
  >
    <div class="error-boundary__icon">
      ⚠️
    </div>
    <h3 class="error-boundary__title">
      出错了
    </h3>
    <p class="error-boundary__message">
      {{ errorMessage }}
    </p>
    <a-button
      type="primary"
      @click="handleRetry"
    >
      重试
    </a-button>
  </div>
  <slot v-else />
</template>

<style scoped>
.error-boundary {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-10);
  text-align: center;
}
.error-boundary__icon {
  font-size: 40px;
  margin-bottom: var(--space-3);
}
.error-boundary__title {
  font-size: var(--text-h4);
  color: var(--color-error);
  margin-bottom: var(--space-2);
}
.error-boundary__message {
  font-size: var(--text-body-sm);
  color: var(--color-text-secondary);
  margin-bottom: var(--space-5);
  max-width: 360px;
}
</style>
