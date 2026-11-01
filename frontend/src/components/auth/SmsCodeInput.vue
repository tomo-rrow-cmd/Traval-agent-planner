<script setup lang="ts">
/* ============================================================
   SmsCodeInput — 短信验证码输入组件
   对应文档：API接口规范文档.md · §2.1
   ============================================================ */

import { ref, computed } from 'vue'

const model = defineModel<string>({ required: true })

const props = withDefaults(defineProps<{
  phone?: string
  disabled?: boolean
  sendDisabled?: boolean
}>(), {
  phone: '',
  disabled: false,
  sendDisabled: false,
})

const emit = defineEmits<{
  sendCode: []
}>()

const countdown = ref(0)
const isSending = ref(false)

const canSend = computed(() => countdown.value <= 0 && !props.disabled && !isSending.value && !props.sendDisabled)
const buttonText = computed(() => {
  if (isSending.value) return '发送中'
  if (countdown.value > 0) return `${countdown.value}s`
  return '获取验证码'
})

async function handleSend() {
  if (!canSend.value) return
  isSending.value = true
  emit('sendCode')
  countdown.value = 60
  const timer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      clearInterval(timer)
    }
  }, 1000)
  isSending.value = false
}

function formatCode(value: string) {
  return value.replace(/\D/g, '').slice(0, 6)
}

function handleInput(e: Event) {
  const target = e.target as HTMLInputElement
  model.value = formatCode(target.value)
}
</script>

<template>
  <div class="sms-input">
    <div class="sms-input__field-wrapper">
      <input
        class="sms-input__field"
        type="text"
        inputmode="numeric"
        placeholder="输入验证码"
        :value="model"
        maxlength="6"
        :disabled="disabled"
        @input="handleInput"
      >
    </div>
    <button
      class="sms-input__send-btn"
      :class="{ 'sms-input__send-btn--active': canSend }"
      :disabled="!canSend"
      @click="handleSend"
    >
      {{ buttonText }}
    </button>
  </div>
</template>

<style scoped>
.sms-input {
  display: flex;
  gap: var(--space-3);
}

.sms-input__field-wrapper {
  flex: 1;
  height: var(--input-height);
  border: 1px solid var(--input-border-color);
  border-radius: var(--input-radius);
  background: var(--color-bg-card);
  transition: all var(--dur-fast) var(--ease-in-out);
  overflow: hidden;
}
.sms-input__field-wrapper:focus-within {
  border-color: var(--color-brand-500);
  box-shadow: var(--input-focus-shadow);
}

.sms-input__field {
  width: 100%;
  height: 100%;
  border: none;
  outline: none;
  padding: 0 var(--space-3);
  font-size: var(--text-body);
  color: var(--color-text-primary);
  background: transparent;
}
.sms-input__field::placeholder {
  color: var(--color-text-placeholder);
}

.sms-input__send-btn {
  flex-shrink: 0;
  height: var(--input-height);
  padding: 0 var(--space-4);
  border: 1px solid var(--color-border);
  border-radius: var(--input-radius);
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
  font-size: var(--text-body-sm);
  font-weight: var(--fw-medium);
  cursor: not-allowed;
  transition: all var(--dur-fast) var(--ease-in-out);
  white-space: nowrap;
}
.sms-input__send-btn--active {
  border-color: var(--color-brand-300);
  background: var(--color-brand-50);
  color: var(--color-brand-600);
  cursor: pointer;
}
.sms-input__send-btn--active:hover {
  background: var(--color-brand-100);
  border-color: var(--color-brand-400);
}
</style>
