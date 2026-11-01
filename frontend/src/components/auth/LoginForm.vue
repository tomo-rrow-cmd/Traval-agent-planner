<script setup lang="ts">
/* ============================================================
   LoginForm — 登录表单（支持验证码/密码切换）
   ============================================================ */

import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'
import PhoneVerifyInput from './PhoneVerifyInput.vue'
import SmsCodeInput from './SmsCodeInput.vue'
import InlineAlert from '@/components/notification/InlineAlert.vue'

type LoginMethod = 'code' | 'password'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const uiStore = useUiStore()

const emit = defineEmits<{
  switchToRegister: []
}>()

const loginMethod = ref<LoginMethod>('code')
const phone = ref('')
const code = ref('')
const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleSendCode() {
  if (phone.value.length !== 11) return
  try {
    await authStore.sendSmsCode(phone.value)
    uiStore.showSuccess('验证码已发送')
  } catch (e: any) {
    error.value = e.message || '发送失败'
  }
}

function toggleMethod() {
  loginMethod.value = loginMethod.value === 'code' ? 'password' : 'code'
  error.value = ''
}

async function handleLogin() {
  if (phone.value.length !== 11) {
    error.value = '请填写正确的手机号'
    return
  }
  if (loginMethod.value === 'code' && code.value.length !== 6) {
    error.value = '请填写完整的验证码'
    return
  }
  if (loginMethod.value === 'password' && !password.value) {
    error.value = '请填写密码'
    return
  }

  loading.value = true
  error.value = ''

  try {
    if (loginMethod.value === 'code') {
      await authStore.login(phone.value, code.value)
    } else {
      await authStore.loginWithPassword(phone.value, password.value)
    }
    // 关闭弹窗
    uiStore.closeLoginModal()
    uiStore.showSuccess('登录成功')

    // 延迟跳转，让过渡动画先执行
    setTimeout(() => {
      const redirect = (route.query.redirect as string) || '/chat'
      router.push(redirect)
    }, 200)
  } catch (e: any) {
    error.value = e.message || '登录失败，请重试'
  } finally {
    loading.value = false
  }
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !loading.value) {
    handleLogin()
  }
}

// 验证码登录是否可提交
const canSubmitCode = () => phone.value.length === 11 && code.value.length === 6
// 密码登录是否可提交
const canSubmitPassword = () => phone.value.length === 11 && password.value.length >= 6
</script>

<template>
  <div class="login-form">
    <div class="login-form__header">
      <h2 class="login-form__title">
        欢迎回来
      </h2>
      <p class="login-form__subtitle">
        登录后即可保存和管理您的旅行方案
      </p>
    </div>

    <div
      v-if="error"
      class="login-form__error"
    >
      <InlineAlert
        type="error"
        :message="error"
        closable
        @close="error = ''"
      />
    </div>

    <div
      class="login-form__fields"
      @keydown="handleKeydown"
    >
      <PhoneVerifyInput v-model="phone" />

      <!-- 输入区域（带切换动画） -->
      <Transition
        name="method-switch"
        mode="out-in"
      >
        <div
          v-if="loginMethod === 'code'"
          key="code"
          class="login-form__method-fields"
        >
          <SmsCodeInput
            v-model="code"
            :phone="phone"
            :send-disabled="phone.length !== 11"
            @send-code="handleSendCode"
          />
        </div>
        <div
          v-else
          key="password"
          class="login-form__method-fields"
        >
          <div class="login-form__input-wrap">
            <input
              v-model="password"
              class="login-form__input"
              type="password"
              placeholder="请输入密码"
              autocomplete="current-password"
            >
          </div>
        </div>
      </Transition>
    </div>

    <!-- 切换登录方式 -->
    <button
      class="login-form__toggle-method"
      type="button"
      @click="toggleMethod"
    >
      {{ loginMethod === 'code' ? '使用密码登录' : '使用验证码登录' }}
    </button>

    <a-button
      type="primary"
      class="login-form__submit"
      :loading="loading"
      :disabled="loginMethod === 'code' ? !canSubmitCode() : !canSubmitPassword()"
      block
      size="large"
      @click="handleLogin"
    >
      {{ loading ? '登录中...' : '登录' }}
    </a-button>

    <div class="login-form__footer">
      <span class="login-form__hint">登录即表示同意</span>
      <a
        class="login-form__link"
        href="#"
      >服务条款</a>
      <span class="login-form__hint">和</span>
      <a
        class="login-form__link"
        href="#"
      >隐私政策</a>
    </div>

    <div class="login-form__switch">
      <span class="login-form__hint">没有账号？</span>
      <button
        class="login-form__switch-btn"
        type="button"
        @click="emit('switchToRegister')"
      >
        去注册 →
      </button>
    </div>
  </div>
</template>

<style scoped>
.login-form {
  width: 100%;
  max-width: 400px;
  display: flex;
  flex-direction: column;
  flex: 1;
}

.login-form__header {
  text-align: center;
  margin-bottom: var(--space-5);
}

.login-form__title {
  font-size: var(--text-h3);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-1);
}

.login-form__subtitle {
  font-size: var(--text-body-sm);
  color: var(--color-text-tertiary);
}

.login-form__error {
  margin-bottom: var(--space-3);
}

.login-form__fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  margin-bottom: var(--space-3);
}

.login-form__method-fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
}

/* 密码输入框 */
.login-form__input-wrap {
  display: flex;
  align-items: center;
  height: var(--input-height);
  border: 1.5px solid var(--input-border-color);
  border-radius: var(--input-radius);
  background: var(--color-bg-card);
  transition: all var(--dur-fast) var(--ease-in-out);
  overflow: hidden;
}
.login-form__input-wrap:focus-within {
  border-color: var(--color-brand-500);
  box-shadow: var(--input-focus-shadow);
}

.login-form__input {
  flex: 1;
  height: 100%;
  border: none;
  outline: none;
  padding: 0 var(--space-3);
  font-size: var(--text-body);
  color: var(--color-text-primary);
  background: transparent;
}
.login-form__input::placeholder {
  color: var(--color-text-placeholder);
}

/* 切换登录方式按钮 */
.login-form__toggle-method {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--space-1);
  padding: var(--space-2) 0;
  border: none;
  background: transparent;
  color: var(--color-text-tertiary);
  font-size: var(--text-small);
  cursor: pointer;
  transition: color var(--dur-fast) var(--ease-in-out);
  margin-bottom: var(--space-3);
}
.login-form__toggle-method:hover {
  color: var(--color-brand-500);
}

.login-form__submit {
  height: 48px;
  font-size: var(--text-body-lg);
  border-radius: var(--radius-sm);
}

.login-form__footer {
  text-align: center;
  margin-top: var(--space-4);
  font-size: var(--text-small);
}

.login-form__hint {
  color: var(--color-text-tertiary);
}

.login-form__link {
  color: var(--color-sky);
  margin: 0 2px;
}

.login-form__switch {
  text-align: center;
  margin-top: var(--space-3);
  padding-top: var(--space-3);
  border-top: 1px solid var(--color-border-light);
  font-size: var(--text-small);
}

.login-form__switch-btn {
  padding: 0;
  border: none;
  background: none;
  color: var(--color-brand-500);
  font-weight: var(--fw-medium);
  font-size: var(--text-small);
  cursor: pointer;
  transition: color var(--dur-fast) var(--ease-in-out);
}
.login-form__switch-btn:hover {
  color: var(--color-brand-600);
  text-decoration: underline;
}

/* ===== 过渡动画：验证码/密码切换 ===== */
.method-switch-enter-active {
  transition: all 0.2s var(--ease-out-expo);
}
.method-switch-leave-active {
  transition: all 0.12s var(--ease-in-out);
}
.method-switch-enter-from {
  opacity: 0;
  transform: translateY(6px);
}
.method-switch-leave-to {
  opacity: 0;
  transform: translateY(-4px);
}
</style>
