<script setup lang="ts">
/* ============================================================
   AppHeader — 全局顶部导航栏（毛玻璃质感）
   对应文档：界面视觉设计系统.md · §7 毛玻璃、§15 导航
   ============================================================ */

import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'
import AppLogo from '@/components/brand/AppLogo.vue'

withDefaults(defineProps<{
  simple?: boolean
}>(), {
  simple: false,
})

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const showUserMenu = computed(() => authStore.isLoggedIn)

function handleThemeToggle() {
  uiStore.setTheme(uiStore.theme === 'light' ? 'dark' : 'light')
}

function goToProfile() {
  router.push('/profile')
}

function goHome() {
  router.push('/')
}
</script>

<template>
  <header
    class="app-header"
    :class="{ 'app-header--simple': simple }"
  >
    <div class="app-header__left">
      <button
        v-if="!simple"
        class="app-header__sidebar-toggle"
        aria-label="切换侧栏"
        @click="uiStore.toggleSidebar()"
      >
        <svg
          width="20"
          height="20"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <line
            x1="3"
            y1="6"
            x2="21"
            y2="6"
          />
          <line
            x1="3"
            y1="12"
            x2="21"
            y2="12"
          />
          <line
            x1="3"
            y1="18"
            x2="21"
            y2="18"
          />
        </svg>
      </button>
      <div
        class="app-header__brand"
        @click="goHome"
      >
        <AppLogo
          :size="24"
          type="icon"
          class="app-header__logo"
        />
        <span class="app-header__title">旅行者</span>
      </div>
    </div>

    <div class="app-header__right">
      <button
        class="app-header__icon-btn"
        :title="uiStore.theme === 'light' ? '切换暗色模式' : '切换亮色模式'"
        @click="handleThemeToggle"
      >
        <svg
          v-if="uiStore.theme === 'light'"
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
        </svg>
        <svg
          v-else
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <circle
            cx="12"
            cy="12"
            r="5"
          />
          <line
            x1="12"
            y1="1"
            x2="12"
            y2="3"
          />
          <line
            x1="12"
            y1="21"
            x2="12"
            y2="23"
          />
          <line
            x1="4.22"
            y1="4.22"
            x2="5.64"
            y2="5.64"
          />
          <line
            x1="18.36"
            y1="18.36"
            x2="19.78"
            y2="19.78"
          />
          <line
            x1="1"
            y1="12"
            x2="3"
            y2="12"
          />
          <line
            x1="21"
            y1="12"
            x2="23"
            y2="12"
          />
          <line
            x1="4.22"
            y1="19.78"
            x2="5.64"
            y2="18.36"
          />
          <line
            x1="18.36"
            y1="5.64"
            x2="19.78"
            y2="4.22"
          />
        </svg>
      </button>
      <button
        v-if="showUserMenu"
        class="app-header__avatar"
        title="个人中心"
        @click="goToProfile"
      >
        <span class="app-header__avatar-text">
          {{ authStore.user?.nickname?.charAt(0) || '旅' }}
        </span>
      </button>
    </div>
  </header>
</template>

<style scoped>
.app-header {
  position: sticky;
  top: 0;
  z-index: var(--z-sticky);
  display: flex;
  align-items: center;
  justify-content: space-between;
  height: var(--header-height);
  padding: 0 var(--space-6);
  background: var(--color-glass-bg);
  backdrop-filter: blur(var(--glass-blur));
  -webkit-backdrop-filter: blur(var(--glass-blur));
  border-bottom: 1px solid var(--color-glass-border);
  transition: background var(--dur-normal) var(--ease-in-out);
}

.app-header--simple {
  padding: 0 var(--space-8);
}

.app-header__left {
  display: flex;
  align-items: center;
  gap: var(--space-3);
}

.app-header__sidebar-toggle {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--dur-fast) var(--ease-in-out);
}
.app-header__sidebar-toggle:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.app-header__brand {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  cursor: pointer;
  user-select: none;
}

.app-header__logo {
  color: var(--color-brand-500);
  display: flex;
  align-items: center;
}

.app-header__title {
  font-size: var(--text-h4);
  font-weight: var(--fw-semibold);
  color: var(--color-brand-600);
  letter-spacing: 0.5px;
}

.app-header__right {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}

.app-header__icon-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: none;
  background: transparent;
  color: var(--color-text-secondary);
  cursor: pointer;
  border-radius: var(--radius-sm);
  transition: all var(--dur-fast) var(--ease-in-out);
}
.app-header__icon-btn:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-brand-500);
}

.app-header__avatar {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-full);
  border: 2px solid var(--color-brand-300);
  background: var(--color-brand-100);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: all var(--dur-fast) var(--ease-in-out);
}
.app-header__avatar:hover {
  border-color: var(--color-brand-500);
  box-shadow: 0 0 0 3px rgba(232, 168, 124, 0.2);
}

.app-header__avatar-text {
  font-size: var(--text-caption);
  font-weight: var(--fw-semibold);
  color: var(--color-brand-700);
}
</style>
