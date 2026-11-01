<script setup lang="ts">
/* ============================================================
   AppLayout — 根布局壳
   对应文档：前端界面设计文档.md · §2
   ============================================================ */

import { onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'

import LoginModal from '@/components/auth/LoginModal.vue'

const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUiStore()

onMounted(() => {
  authStore.initializeSession()
  uiStore.initTheme()

  // 断点检测
  const checkBreakpoint = () => {
    const w = window.innerWidth
    if (w < 576) uiStore.setBreakpoint('xs')
    else if (w < 768) uiStore.setBreakpoint('sm')
    else if (w < 1024) uiStore.setBreakpoint('md')
    else uiStore.setBreakpoint('lg')
  }
  checkBreakpoint()
  window.addEventListener('resize', checkBreakpoint)
})
</script>

<template>
  <div
    class="app-root"
    :class="{ 'sidebar-collapsed': uiStore.sidebarCollapsed }"
  >
    <router-view v-slot="{ Component }">
      <Transition
        name="page"
        mode="out-in"
      >
        <component
          :is="Component"
          :key="route.path"
        />
      </Transition>
    </router-view>

    <!-- 全局登录弹窗 -->
    <LoginModal />
  </div>
</template>

<style scoped>
.app-root {
  min-height: 100vh;
  background: var(--color-bg-primary);
  color: var(--color-text-primary);
  transition: background var(--dur-normal) var(--ease-in-out);
}

/* 页面过渡动画 */
.page-enter-active {
  transition: all 0.4s var(--ease-out-expo);
}
.page-leave-active {
  transition: all 0.25s var(--ease-in-out);
}
.page-enter-from {
  opacity: 0;
  transform: translateY(16px) scale(0.98);
}
.page-leave-to {
  opacity: 0;
  transform: translateY(-8px) scale(0.99);
}
</style>
