<script setup lang="ts">
/* ============================================================
   RegisterForm — 注册表单（内联版，用于 LoginModal）
   ============================================================ */

import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/store/authStore'
import { useUiStore } from '@/store/uiStore'
import PhoneVerifyInput from './PhoneVerifyInput.vue'
import InlineAlert from '@/components/notification/InlineAlert.vue'

const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

const emit = defineEmits<{
  switchToLogin: []
}>()

const phone = ref('')
const nickname = ref('')
const password = ref('')
const confirmPassword = ref('')
const submitting = ref(false)
const error = ref('')

const passwordError = computed(() => {
  if (password.value && password.value.length < 6) return '密码至少6位'
  if (password.value && password.value.length > 64) return '密码不能超过64位'
  if (confirmPassword.value && password.value !== confirmPassword.value) return '两次密码不一致'
  return ''
})

const canSubmit = computed(() => {
  return (
    phone.value.length === 11 &&
    password.value.length >= 6 &&
    password.value === confirmPassword.value
  )
})

async function handleRegister() {
  if (!canSubmit.value || submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    await authStore.register(phone.value, password.value, nickname.value || undefined)
    // 注册成功后自动关闭弹窗 + 跳转到对话页
    uiStore.closeLoginModal()
    uiStore.showSuccess('注册成功！')

    // 延迟跳转，让关闭弹窗动画先执行
    setTimeout(() => {
      router.push('/chat')
    }, 200)
  } catch (e: any) {
    error.value = e.message || '注册失败，请重试'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="register-form">
    <div class="register-form__header">
      <h2 class="register-form__title">
        创建账号
      </h2>
      <p class="register-form__subtitle">
        开启您的 AI 旅行规划之旅
      </p>
    </div>

    <div
      v-if="error"
      class="register-form__error"
    >
      <InlineAlert
        type="error"
        :message="error"
        closable
        @close="error = ''"
      />
    </div>

    <form
      class="register-form__body"
      @submit.prevent="handleRegister"
    >
      <div class="register-form__fields">
        <div class="register-form__field-label">
          手机号 <span class="register-form__required">*</span>
        </div>
        <PhoneVerifyInput
          v-model="phone"
          :disabled="submitting"
        />

        <div class="register-form__field-label">
          昵称<span class="register-form__optional">（选填）</span>
        </div>
        <div class="register-form__input-wrapper">
          <input
            v-model="nickname"
            class="register-form__input"
            type="text"
            placeholder="您希望我们怎么称呼您？"
            maxlength="30"
            :disabled="submitting"
          >
        </div>

        <div class="register-form__field-label">
          设置密码 <span class="register-form__required">*</span>
        </div>
        <div
          class="register-form__input-wrapper"
          :class="{ 'register-form__input-wrapper--error': passwordError && password }"
        >
          <input
            v-model="password"
            class="register-form__input"
            type="password"
            placeholder="至少6位，建议包含字母和数字"
            autocomplete="new-password"
            :disabled="submitting"
          >
        </div>
        <p
          v-if="passwordError && password"
          class="register-form__field-error"
        >
          {{ passwordError }}
        </p>

        <div class="register-form__field-label">
          确认密码 <span class="register-form__required">*</span>
        </div>
        <div
          class="register-form__input-wrapper"
          :class="{ 'register-form__input-wrapper--error': confirmPassword && password !== confirmPassword }"
        >
          <input
            v-model="confirmPassword"
            class="register-form__input"
            type="password"
            placeholder="再次输入密码"
            autocomplete="new-password"
            :disabled="submitting"
          >
        </div>
      </div>

      <a-button
        type="primary"
        html-type="submit"
        class="register-form__submit"
        :loading="submitting"
        :disabled="!canSubmit"
        block
        size="large"
      >
        {{ submitting ? '注册中...' : '注册' }}
      </a-button>

      <div class="register-form__footer">
        <span class="register-form__footer-hint">已有账号？</span>
        <button
          class="register-form__footer-link"
          type="button"
          @click="emit('switchToLogin')"
        >
          去登录 →
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.register-form {
  width: 100%;
  max-width: 400px;
}

.register-form__header {
  text-align: center;
  margin-bottom: var(--space-6);
}

.register-form__title {
  font-size: var(--text-h2);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.register-form__subtitle {
  font-size: var(--text-body-sm);
  color: var(--color-text-tertiary);
}

.register-form__error {
  margin-bottom: var(--space-4);
}

.register-form__body {
  display: flex;
  flex-direction: column;
}

.register-form__fields {
  display: flex;
  flex-direction: column;
  gap: var(--space-4);
  margin-bottom: var(--space-6);
}

.register-form__field-label {
  font-size: var(--text-body-sm);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
  margin-bottom: -2px;
}

.register-form__required {
  color: var(--color-error);
}

.register-form__optional {
  color: var(--color-text-tertiary);
  font-weight: var(--fw-regular);
}

.register-form__input-wrapper {
  display: flex;
  align-items: center;
  height: var(--input-height);
  border: 1px solid var(--input-border-color);
  border-radius: var(--input-radius);
  background: var(--color-bg-card);
  transition: all var(--dur-fast) var(--ease-in-out);
  overflow: hidden;
}
.register-form__input-wrapper:focus-within {
  border-color: var(--color-brand-500);
  box-shadow: var(--input-focus-shadow);
}
.register-form__input-wrapper--error {
  border-color: var(--color-error);
}
.register-form__input-wrapper--error:focus-within {
  border-color: var(--color-error);
  box-shadow: var(--input-error-shadow);
}

.register-form__input {
  flex: 1;
  height: 100%;
  border: none;
  outline: none;
  padding: 0 var(--space-3);
  font-size: var(--text-body);
  color: var(--color-text-primary);
  background: transparent;
}
.register-form__input::placeholder {
  color: var(--color-text-placeholder);
}

.register-form__field-error {
  font-size: var(--text-small);
  color: var(--color-error);
  margin-top: -2px;
}

.register-form__submit {
  height: 48px;
  font-size: var(--text-body-lg);
  border-radius: var(--radius-sm);
}

.register-form__footer {
  text-align: center;
  margin-top: var(--space-6);
  font-size: var(--text-body-sm);
}

.register-form__footer-hint {
  color: var(--color-text-tertiary);
}

.register-form__footer-link {
  padding: 0;
  border: none;
  background: none;
  color: var(--color-brand-500);
  font-weight: var(--fw-medium);
  font-size: var(--text-body-sm);
  cursor: pointer;
  transition: color var(--dur-fast) var(--ease-in-out);
}
.register-form__footer-link:hover {
  color: var(--color-brand-600);
  text-decoration: underline;
}
</style>
