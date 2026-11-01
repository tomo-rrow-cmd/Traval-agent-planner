<script setup lang="ts">
/* ============================================================
   EmptyState — 空状态组件
   对应文档：前端界面设计文档.md · §8.4.2
   ============================================================ */

withDefaults(defineProps<{
  type?: 'default' | 'search' | 'error' | 'favorite'
  title?: string
  description?: string
  actionText?: string
}>(), {
  type: 'default',
  title: '暂无内容',
  description: '这里空空如也',
  actionText: '',
})

import IconTravel from "@/components/icons/IconTravel.vue"

const emit = defineEmits<{
  action: []
}>()

const iconMap: Record<string, string> = {
  default: 'compass',
  search: 'compass',
  error: 'close',
  favorite: 'star',
}
</script>

<template>
  <div class="empty-state">
    <IconTravel
      :name="iconMap[type]"
      :size="40"
      class="empty-state__icon"
    />
    <h3 class="empty-state__title">
      {{ title }}
    </h3>
    <p class="empty-state__desc">
      {{ description }}
    </p>
    <a-button
      v-if="actionText"
      type="primary"
      @click="emit('action')"
    >
      {{ actionText }}
    </a-button>
  </div>
</template>

<style scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: var(--space-12) var(--space-6);
  text-align: center;
}

.empty-state__icon {
  margin-bottom: var(--space-4);
  color: var(--color-brand-400);
}

.empty-state__title {
  font-size: var(--text-h4);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
  margin-bottom: var(--space-2);
}

.empty-state__desc {
  font-size: var(--text-body-sm);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-6);
  max-width: 300px;
}
</style>
