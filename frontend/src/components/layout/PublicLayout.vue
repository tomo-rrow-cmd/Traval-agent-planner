<script setup lang="ts">
/* ============================================================
   PublicLayout — 简洁裸露布局
   用于首页/登录/注册，无侧栏干扰
   对应文档：前端界面设计文档.md · §2
   ============================================================ */
</script>

<template>
  <main class="public-layout">
    <router-view />
  </main>
</template>

<style scoped>
.public-layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, var(--color-bg-primary) 0%, var(--color-brand-50) 100%);
}
</style>
