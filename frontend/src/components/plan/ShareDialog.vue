<script setup lang="ts">
/* ============================================================
   ShareDialog — 分享弹窗
   对应文档：前端界面设计文档.md · §4.5
   ============================================================ */

import { ref } from 'vue'
import { useUiStore } from '@/store/uiStore'

withDefaults(defineProps<{
  visible?: boolean
  planTitle?: string
}>(), {
  visible: false,
  planTitle: '',
})

const emit = defineEmits<{
  'update:visible': [v: boolean]
  share: [options: { expire_in?: number; password?: string }]
}>()

const uiStore = useUiStore()
const expireIn = ref<number | undefined>(86400)
const password = ref('')

const expireOptions = [
  { value: undefined, label: '永不过期' },
  { value: 86400, label: '1 天' },
  { value: 259200, label: '3 天' },
  { value: 604800, label: '7 天' },
  { value: 2592000, label: '30 天' },
]

function handleGenerate() {
  emit('share', {
    expire_in: expireIn.value,
    password: password.value || undefined,
  })
  uiStore.showSuccess('分享链接已生成')
  emit('update:visible', false)
}

function handleClose() {
  emit('update:visible', false)
}
</script>

<template>
  <a-modal
    :open="visible"
    title="分享方案"
    :footer="null"
    width="420px"
    :centered="true"
    :destroy-on-close="true"
    @cancel="handleClose"
  >
    <div class="share-dialog">
      <div
        v-if="planTitle"
        class="share-dialog__plan"
      >
        <span class="share-dialog__plan-icon">📋</span>
        <span>{{ planTitle }}</span>
      </div>

      <div class="share-dialog__field">
        <label class="share-dialog__label">过期时间</label>
        <div class="share-dialog__expire-options">
          <a-tag
            v-for="opt in expireOptions"
            :key="opt.label"
            :color="expireIn === opt.value ? 'var(--color-brand-500)' : ''"
            class="share-dialog__tag"
            :class="{ 'share-dialog__tag--active': expireIn === opt.value }"
            @click="expireIn = opt.value"
          >
            {{ opt.label }}
          </a-tag>
        </div>
      </div>

      <div class="share-dialog__field">
        <label class="share-dialog__label">访问密码（可选）</label>
        <a-input-password
          v-model:value="password"
          placeholder="设置密码后，仅知道密码的人可查看"
        />
      </div>

      <a-button
        type="primary"
        block
        size="large"
        class="share-dialog__btn"
        @click="handleGenerate"
      >
        🔗 生成分享链接
      </a-button>
    </div>
  </a-modal>
</template>

<style scoped>
.share-dialog {
  display: flex;
  flex-direction: column;
  gap: var(--space-5);
}

.share-dialog__plan {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  padding: var(--space-3) var(--space-4);
  background: var(--color-brand-50);
  border-radius: var(--radius-sm);
  font-size: var(--text-body);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
}

.share-dialog__plan-icon {
  font-size: 20px;
}

.share-dialog__field {
  display: flex;
  flex-direction: column;
  gap: var(--space-2);
}

.share-dialog__label {
  font-size: var(--text-body-sm);
  font-weight: var(--fw-medium);
  color: var(--color-text-secondary);
}

.share-dialog__expire-options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--space-2);
}

.share-dialog__tag {
  cursor: pointer !important;
  padding: 4px 16px !important;
  border-radius: var(--radius-pill) !important;
  border: 1px solid var(--color-border) !important;
  color: var(--color-text-secondary) !important;
  background: var(--color-bg-card) !important;
  font-size: var(--text-body-sm) !important;
  transition: all var(--dur-fast);
}
.share-dialog__tag:hover {
  border-color: var(--color-brand-300) !important;
}
.share-dialog__tag--active {
  background: var(--color-brand-50) !important;
  border-color: var(--color-brand-500) !important;
  color: var(--color-brand-700) !important;
  font-weight: var(--fw-medium) !important;
}

.share-dialog__btn {
  height: 44px;
  font-size: var(--text-body);
  margin-top: var(--space-2);
}
</style>
