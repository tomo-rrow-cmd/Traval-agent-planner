<script setup lang="ts">
/* ============================================================
   ConfirmDialog — 确认弹窗
   ============================================================ */

import { ref } from 'vue'

withDefaults(defineProps<{
  visible: boolean
  title?: string
  content?: string
  okText?: string
  cancelText?: string
  danger?: boolean
}>(), {
  title: '确认操作',
  content: '确定要执行此操作吗？',
  okText: '确定',
  cancelText: '取消',
  danger: false,
})

const emit = defineEmits<{
  (e: 'update:visible', v: boolean): void
  (e: 'confirm'): void
}>()

const loading = ref(false)

async function handleOk() {
  loading.value = true
  emit('confirm')
  loading.value = false
}

function handleCancel() {
  emit('update:visible', false)
}
</script>

<template>
  <a-modal
    :open="visible"
    :title="title"
    :ok-text="okText"
    :cancel-text="cancelText"
    :confirm-loading="loading"
    :ok-button-props="{ danger: danger }"
    :width="400"
    :centered="true"
    :mask-closable="false"
    @ok="handleOk"
    @cancel="handleCancel"
  >
    <p class="confirm-content">
      {{ content }}
    </p>
  </a-modal>
</template>

<style scoped>
.confirm-content {
  font-size: var(--text-body);
  color: var(--color-text-secondary);
  line-height: var(--lh-relaxed);
}
</style>
