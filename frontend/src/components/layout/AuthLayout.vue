<script setup lang="ts">
/* ============================================================
   AuthLayout — 侧栏 + 主内容区布局
   对应文档：前端界面设计文档.md · §2
   ============================================================ */

import AppSidebar from '@/components/common/AppSidebar.vue'
import AppHeader from '@/components/common/AppHeader.vue'
</script>

<template>
  <div class="auth-layout">
    <AppSidebar />
    <div class="auth-content">
      <AppHeader />
      <div class="auth-main">
        <router-view />
      </div>
    </div>
  </div>
</template>

<style scoped>
.auth-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}
.auth-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
  background: var(--color-bg-primary);
}
.auth-main {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
}
</style>
