<script setup lang="ts">
/* ============================================================
   ActivityDrawer — 活动替换/修改抽屉面板
   对应文档：前端界面设计文档.md · §4.2、§4.3
   ============================================================ */

import { ref } from 'vue'
import type { ActivityType } from '@/types/plan'
import { ACTIVITY_TYPE_LABELS } from '@/types/plan'

withDefaults(defineProps<{
  visible?: boolean
  currentActivity?: {
    title: string
    type: ActivityType
    description?: string
  }
}>(), {
  visible: false,
  currentActivity: undefined,
})

const emit = defineEmits<{
  'update:visible': [v: boolean]
  replace: [reason: string]
  close: []
}>()

const reason = ref('')

// 候选替换建议（硬编码示例，对接后端后改为动态）
const candidates = [
  { title: '替换选项一', type: 'food' as ActivityType, desc: '相似风格替代', rating: 4.3 },
  { title: '替换选项二', type: 'food' as ActivityType, desc: '更受欢迎的选择', rating: 4.5 },
  { title: '替换选项三', type: 'attraction' as ActivityType, desc: '同区域其他推荐', rating: 4.2 },
  { title: '替换选项四', type: 'food' as ActivityType, desc: '性价比更高的选择', rating: 4.0 },
  { title: '替换选项五', type: 'entertainment' as ActivityType, desc: '全新体验', rating: 4.6 },
]

function handleReplace(idx: number) {
  reason.value = candidates[idx].title
  emit('replace', candidates[idx].title)
}

function handleClose() {
  emit('update:visible', false)
  emit('close')
}
</script>

<template>
  <a-drawer
    :open="visible"
    title="替换活动"
    placement="bottom"
    height="60%"
    :closable="true"
    :style="{ borderRadius: '16px 16px 0 0' }"
    @close="handleClose"
  >
    <!-- 当前活动 -->
    <div
      v-if="currentActivity"
      class="activity-drawer__current"
    >
      <div class="activity-drawer__current-label">
        当前活动
      </div>
      <div class="activity-drawer__current-card">
        <span class="activity-drawer__current-type">{{ ACTIVITY_TYPE_LABELS[currentActivity.type] }}</span>
        <span class="activity-drawer__current-title">{{ currentActivity.title }}</span>
      </div>
    </div>

    <!-- 候选列表 -->
    <div class="activity-drawer__candidates">
      <div class="activity-drawer__candidates-label">
        推荐替换（至多 5 个选项）
      </div>
      <div
        v-for="(item, idx) in candidates"
        :key="idx"
        class="activity-drawer__candidate"
        @click="handleReplace(idx)"
      >
        <div class="activity-drawer__candidate-info">
          <span class="activity-drawer__candidate-type">{{ ACTIVITY_TYPE_LABELS[item.type] }}</span>
          <span class="activity-drawer__candidate-title">{{ item.title }}</span>
          <span class="activity-drawer__candidate-desc">{{ item.desc }}</span>
        </div>
        <div class="activity-drawer__candidate-rating">
          <span>⭐ {{ item.rating }}</span>
          <span class="activity-drawer__candidate-arrow">→</span>
        </div>
      </div>
    </div>
  </a-drawer>
</template>

<style scoped>
.activity-drawer__current {
  margin-bottom: var(--space-6);
}

.activity-drawer__current-label {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-2);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.activity-drawer__current-card {
  display: flex;
  align-items: center;
  gap: var(--space-3);
  padding: var(--space-3) var(--space-4);
  background: var(--color-brand-50);
  border: 1px solid var(--color-brand-100);
  border-radius: var(--radius-sm);
}

.activity-drawer__current-type {
  font-size: var(--text-small);
  padding: 1px 6px;
  background: var(--color-brand-200);
  color: var(--color-brand-700);
  border-radius: var(--radius-pill);
}

.activity-drawer__current-title {
  font-size: var(--text-body);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
}

.activity-drawer__candidates-label {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
  margin-bottom: var(--space-3);
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.activity-drawer__candidate {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: var(--space-3) var(--space-4);
  border: 1px solid var(--color-border-light);
  border-radius: var(--radius-sm);
  margin-bottom: var(--space-2);
  cursor: pointer;
  transition: all var(--dur-fast) var(--ease-in-out);
}
.activity-drawer__candidate:hover {
  background: var(--color-brand-50);
  border-color: var(--color-brand-200);
}

.activity-drawer__candidate-info {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.activity-drawer__candidate-type {
  font-size: 11px;
  padding: 1px 6px;
  background: var(--color-bg-secondary);
  color: var(--color-text-tertiary);
  border-radius: var(--radius-pill);
  align-self: flex-start;
}

.activity-drawer__candidate-title {
  font-size: var(--text-body);
  font-weight: var(--fw-medium);
  color: var(--color-text-primary);
}

.activity-drawer__candidate-desc {
  font-size: var(--text-small);
  color: var(--color-text-tertiary);
}

.activity-drawer__candidate-rating {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  font-size: var(--text-body-sm);
  color: var(--color-gold);
}

.activity-drawer__candidate-arrow {
  color: var(--color-text-tertiary);
  font-size: 16px;
}
</style>
