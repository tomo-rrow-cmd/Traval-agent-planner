<script setup lang="ts">
/* ============================================================
   PhoneVerifyInput — 手机号输入组件
   对应文档：API接口规范文档.md · §2.1
   ============================================================ */

const model = defineModel<string>({ required: true })

defineEmits<{
  sendCode: []
}>()

function formatPhone(value: string) {
  // 仅允许数字
  return value.replace(/\D/g, '').slice(0, 11)
}

function handleInput(e: Event) {
  const target = e.target as HTMLInputElement
  model.value = formatPhone(target.value)
}
</script>

<template>
  <div class="phone-input">
    <div class="phone-input__prefix">
      <span class="phone-input__country-code">+86</span>
    </div>
    <input
      class="phone-input__field"
      type="tel"
      placeholder="请输入手机号"
      :value="model"
      maxlength="11"
      @input="handleInput"
    >
  </div>
</template>

<style scoped>
.phone-input {
  display: flex;
  align-items: center;
  height: var(--input-height);
  border: 1px solid var(--input-border-color);
  border-radius: var(--input-radius);
  background: var(--color-bg-card);
  transition: all var(--dur-fast) var(--ease-in-out);
  overflow: hidden;
}
.phone-input:focus-within {
  border-color: var(--color-brand-500);
  box-shadow: var(--input-focus-shadow);
}

.phone-input__prefix {
  display: flex;
  align-items: center;
  padding: 0 var(--space-3);
  border-right: 1px solid var(--color-border);
  height: 100%;
}

.phone-input__country-code {
  font-size: var(--text-body);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
}

.phone-input__field {
  flex: 1;
  height: 100%;
  border: none;
  outline: none;
  padding: 0 var(--space-3);
  font-size: var(--text-body);
  color: var(--color-text-primary);
  background: transparent;
}
.phone-input__field::placeholder {
  color: var(--color-text-placeholder);
}
</style>
