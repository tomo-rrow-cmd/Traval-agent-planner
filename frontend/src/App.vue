<script setup lang="ts">
import { onMounted } from 'vue'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'

const authStore = useAuthStore()
const uiStore = useUiStore()

onMounted(() => {
  authStore.initializeSession()

  // 初始化主题
  uiStore.initTheme()

  // 监听系统主题变化
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
    if (!localStorage.getItem('theme')) {
      uiStore.setTheme(e.matches ? 'dark' : 'light')
    }
  })
})
</script>

<template>
  <a-config-provider
    :theme="{
      token: {
        colorPrimary: '#E8A87C',
        borderRadius: 6,
        colorBgContainer: uiStore.theme === 'dark' ? '#2A2826' : '#FFFFFF',
        colorBgLayout: '#FCF9F5',
        colorText: '#2C2C2C',
        colorTextSecondary: '#6B6B6B',
        colorBorder: '#E8E0D6',
        fontSize: 15,
      },
    }"
  >
    <router-view />
  </a-config-provider>
</template>

<style scoped>
/* Root layout - handled by layout components */
</style>
