<script setup lang="ts">
/* ============================================================
   RegisterPage — 注册页（暂时禁用）
   后端未就绪，引导用户直接使用
   ============================================================ */

import { useRouter } from 'vue-router'

const router = useRouter()

function goHome() {
  router.push('/')
}
</script>

<template>
  <div class="register-page">
    <div class="register-page__glass">
      <div class="register-page__icon">
        🔐
      </div>
      <h2 class="register-page__title">
        注册功能开发中
      </h2>
      <p class="register-page__desc">
        当前版本暂无需注册，直接开始规划您的旅程吧
      </p>
      <a-button
        type="primary"
        size="large"
        class="register-page__btn"
        @click="goHome"
      >
        开始规划旅程
      </a-button>
      <p class="register-page__hint">
        <router-link to="/login">
          前往登录 →
        </router-link>
      </p>
    </div>
  </div>
</template>

<style scoped>
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--gradient-hero);
  padding: var(--space-6);
}

.register-page__glass {
  text-align: center;
  padding: var(--space-10) var(--space-8);
  max-width: 400px;
  width: 100%;
  background: var(--color-glass-bg);
  backdrop-filter: blur(20px) saturate(1.2);
  border-radius: var(--radius-lg);
  border: 1px solid rgba(255, 255, 255, 0.4);
  box-shadow: 0 8px 40px rgba(139, 115, 85, 0.1);
}

.register-page__icon {
  font-size: 48px;
  margin-bottom: var(--space-4);
}

.register-page__title {
  font-size: var(--text-h3);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.register-page__desc {
  font-size: var(--text-body);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-6);
  line-height: 1.5;
}

.register-page__btn {
  height: 44px;
  padding: 0 32px;
  border-radius: 10px;
}

.register-page__hint {
  margin-top: var(--space-4);
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
}

.register-page__hint a {
  color: var(--color-brand-500);
}
</style>
