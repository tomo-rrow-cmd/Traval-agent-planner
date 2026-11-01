<script setup lang="ts">
import { useAuthStore } from '@/store/authStore'
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const router = useRouter()

function handleLogout() {
  authStore.clearSession()
  router.push('/')
}
</script>

<template>
  <div class="profile-page">
    <div class="profile-page__card">
      <div class="profile-page__avatar">
        <span>{{ authStore.user?.nickname?.charAt(0) || '旅' }}</span>
      </div>
      <h2 class="profile-page__name">
        {{ authStore.user?.nickname || '旅行者' }}
      </h2>
      <p class="profile-page__phone">
        {{ authStore.user?.phone || '' }}
      </p>
    </div>

    <div class="profile-page__menu">
      <router-link
        to="/profile/preferences"
        class="profile-menu-item"
      >
        <span class="profile-menu-item__icon">⚙️</span>
        <span>偏好设置</span>
        <span class="profile-menu-item__arrow">→</span>
      </router-link>
      <router-link
        to="/plans"
        class="profile-menu-item"
      >
        <span class="profile-menu-item__icon">📋</span>
        <span>我的方案</span>
        <span class="profile-menu-item__arrow">→</span>
      </router-link>
    </div>

    <a-button
      danger
      block
      class="profile-page__logout"
      @click="handleLogout"
    >
      退出登录
    </a-button>
  </div>
</template>

<style scoped>
.profile-page {
  max-width: 480px;
  margin: 0 auto;
  padding: var(--space-6) 0;
}
.profile-page__card {
  text-align: center;
  padding: var(--space-8);
  background: var(--color-bg-card);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-float);
  margin-bottom: var(--space-6);
}
.profile-page__avatar {
  width: 72px; height: 72px; border-radius: 50%;
  background: var(--color-brand-100);
  border: 3px solid var(--color-brand-300);
  display: flex; align-items: center; justify-content: center;
  font-size: var(--text-h2); color: var(--color-brand-600);
  margin: 0 auto var(--space-4);
}
.profile-page__name {
  font-size: var(--text-h3); font-weight: var(--fw-semibold);
  margin-bottom: var(--space-1);
}
.profile-page__phone { color: var(--color-text-tertiary); font-size: var(--text-body-sm); }
.profile-page__menu {
  display: flex; flex-direction: column; gap: var(--space-2);
  margin-bottom: var(--space-8);
}
.profile-menu-item {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-4) var(--space-5);
  background: var(--color-bg-card); border-radius: var(--radius-md);
  box-shadow: var(--shadow-float); color: var(--color-text-primary);
  text-decoration: none; transition: all var(--dur-fast);
}
.profile-menu-item:hover { background: var(--color-brand-50); }
.profile-menu-item__icon { font-size: 20px; }
.profile-menu-item__arrow { margin-left: auto; color: var(--color-text-tertiary); }
</style>
