<script setup lang="ts">
/* ============================================================
   LoginModal — 登录/注册弹窗（底部切换，带淡入过渡）
   ============================================================ */

import { ref } from 'vue'
import { useUiStore } from '@/store/uiStore'
import AppLogo from '@/components/brand/AppLogo.vue'
import LoginForm from './LoginForm.vue'
import RegisterForm from './RegisterForm.vue'

type AuthTab = 'login' | 'register'

const uiStore = useUiStore()
const currentTab = ref<AuthTab>('login')

function handleClose() {
  uiStore.closeLoginModal()
}

function switchToLogin() {
  currentTab.value = 'login'
}

function switchToRegister() {
  currentTab.value = 'register'
}
</script>

<template>
  <Transition name="modal">
    <div
      v-if="uiStore.loginModalVisible"
      class="login-modal"
      @click.self="handleClose"
    >
      <div
        class="login-modal__backdrop"
        @click="handleClose"
      />

      <div class="login-modal__panel">
        <button
          class="login-modal__close"
          @click="handleClose"
        >
          <svg
            width="18"
            height="18"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
          >
            <line
              x1="18"
              y1="6"
              x2="6"
              y2="18"
            /><line
              x1="6"
              y1="6"
              x2="18"
              y2="18"
            />
          </svg>
        </button>

        <div class="login-modal__brand">
          <AppLogo
            :size="36"
            class="login-modal__logo"
          />
          <span class="login-modal__title">旅行者</span>
        </div>

        <!-- 表单区域（带切换过渡动画） -->
        <div class="login-modal__form-wrap">
          <Transition
            name="form-fade"
            mode="out-in"
          >
            <LoginForm
              v-if="currentTab === 'login'"
              key="login"
              @switch-to-register="switchToRegister"
            />
            <RegisterForm
              v-else
              key="register"
              @switch-to-login="switchToLogin"
            />
          </Transition>
        </div>
      </div>
    </div>
  </Transition>
</template>

<style scoped>
.login-modal {
  position: fixed;
  inset: 0;
  z-index: var(--z-modal);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--space-4);
}

.login-modal__backdrop {
  position: absolute;
  inset: 0;
  background: rgba(44, 44, 44, 0.35);
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

.login-modal__panel {
  position: relative;
  width: 100%;
  max-width: 420px;
  padding: var(--space-6) var(--space-6) var(--space-4);
  background: var(--color-bg-card);
  border-radius: var(--radius-lg);
  box-shadow: 0 16px 48px rgba(44, 44, 44, 0.15);
  animation: panelIn 0.35s var(--ease-out-expo);
}

@keyframes panelIn {
  from { opacity: 0; transform: translateY(20px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.login-modal__close {
  position: absolute;
  top: var(--space-3);
  right: var(--space-3);
  width: 32px;
  height: 32px;
  border: none;
  background: var(--color-bg-secondary);
  border-radius: var(--radius-full);
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  color: var(--color-text-tertiary);
  transition: all var(--dur-fast) var(--ease-in-out);
}
.login-modal__close:hover {
  background: var(--color-bg-tertiary);
  color: var(--color-text-primary);
}

.login-modal__brand {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-2);
  margin-bottom: var(--space-5);
}

.login-modal__logo {
  color: var(--color-brand-500);
}

.login-modal__title {
  font-size: var(--text-h4);
  font-weight: 700;
  color: var(--color-brand-600);
  letter-spacing: 0.5px;
}

/* 表单包裹器（固定内容区） */
.login-modal__form-wrap {
  min-height: 320px;
  display: flex;
  flex-direction: column;
}

/* Vue Transition — 弹窗开/关 */
.modal-enter-active {
  transition: opacity 0.3s var(--ease-out-expo);
}
.modal-leave-active {
  transition: opacity 0.2s var(--ease-in-out);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

/* Vue Transition — 表单切换淡入淡出 */
.form-fade-enter-active {
  transition: all 0.25s var(--ease-out-expo);
}
.form-fade-leave-active {
  transition: all 0.15s var(--ease-in-out);
}
.form-fade-enter-from {
  opacity: 0;
  transform: translateY(8px);
}
.form-fade-leave-to {
  opacity: 0;
  transform: translateY(-6px);
}
</style>
