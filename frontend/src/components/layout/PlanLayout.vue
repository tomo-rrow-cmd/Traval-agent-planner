<script setup lang="ts">
/* ============================================================
   PlanLayout — 沉浸式全宽布局（方案详情专用）
   对应文档：前端界面设计文档.md · §2
   ============================================================ */

import AppHeader from '@/components/common/AppHeader.vue'
</script>

<template>
  <div class="plan-layout">
    <AppHeader :simple="true" />
    <div class="plan-main">
      <router-view />
    </div>
  </div>
</template>

<style scoped>
.plan-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-primary);
}
.plan-main {
  flex: 1;
  overflow-y: auto;
}
</style>
