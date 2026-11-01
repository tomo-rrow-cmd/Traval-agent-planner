<script setup lang="ts">
/* ============================================================
   LoadingSpinner — 加载动画
   ============================================================ */

withDefaults(defineProps<{
  tip?: string
  size?: 'small' | 'default' | 'large'
}>(), {
  tip: '',
  size: 'default',
})
</script>

<template>
  <div
    class="loading-spinner"
    :class="`loading-spinner--${size}`"
  >
    <a-spin
      :tip="tip"
      :size="size"
    >
      <template #indicator>
        <div class="loading-spinner__ring">
          <div class="loading-spinner__circle" />
        </div>
      </template>
    </a-spin>
  </div>
</template>

<style scoped>
.loading-spinner {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-8);
}
.loading-spinner--small {
  padding: var(--space-4);
}
.loading-spinner--large {
  padding: var(--space-12);
}

.loading-spinner__ring {
  position: relative;
  width: 32px;
  height: 32px;
}
.loading-spinner--small .loading-spinner__ring {
  width: 20px;
  height: 20px;
}
.loading-spinner--large .loading-spinner__ring {
  width: 48px;
  height: 48px;
}

.loading-spinner__circle {
  width: 100%;
  height: 100%;
  border: 3px solid var(--color-border);
  border-top-color: var(--color-brand-500);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
.loading-spinner--small .loading-spinner__circle {
  border-width: 2px;
}
.loading-spinner--large .loading-spinner__circle {
  border-width: 4px;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
