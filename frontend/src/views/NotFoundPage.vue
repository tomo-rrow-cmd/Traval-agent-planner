<script setup lang="ts">
import { useRouter } from 'vue-router'
const router = useRouter()
</script>

<template>
  <div class="not-found">
    <div class="not-found__icon">
      🗺️
    </div>
    <h1 class="not-found__code">
      404
    </h1>
    <p class="not-found__text">
      您要找的页面好像迷路了
    </p>
    <a-button
      type="primary"
      size="large"
      @click="router.push('/')"
    >
      回到首页
    </a-button>
  </div>
</template>

<style scoped>
.not-found { display: flex; flex-direction: column; align-items: center; justify-content: center; min-height: 60vh; text-align: center; }
.not-found__icon { font-size: 64px; margin-bottom: var(--space-4); }
.not-found__code { font-size: 72px; font-weight: var(--fw-bold); color: var(--color-brand-500); line-height: 1; margin-bottom: var(--space-3); }
.not-found__text { font-size: var(--text-body-lg); color: var(--color-text-tertiary); margin-bottom: var(--space-8); }
</style>
