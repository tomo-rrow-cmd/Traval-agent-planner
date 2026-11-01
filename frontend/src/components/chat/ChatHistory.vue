<script setup lang="ts">
/* ============================================================
   ChatHistory — 历史消息列表（旅行手账风格）
   ============================================================ */

import { ref, watch, nextTick } from 'vue'
import type { Message } from '@/types/chat'
import AppLogo from "@/components/brand/AppLogo.vue"
import ChatMessage from './ChatMessage.vue'

const props = defineProps<{
  messages: Message[]
  loading?: boolean
}>()

const listRef = ref<HTMLDivElement>()

// 新消息和流式内容增长时自动滚动到底部
watch(
  () => {
    const latest = props.messages[props.messages.length - 1]
    return [props.messages.length, latest?.content.length ?? 0]
  },
  async () => {
    await nextTick()
    if (listRef.value) {
      listRef.value.scrollTop = listRef.value.scrollHeight
    }
  },
)
</script>

<template>
  <div
    ref="listRef"
    class="chat-history"
  >
    <!-- 加载态 -->
    <div
      v-if="loading"
      class="chat-history__loading"
    >
      <a-spin size="small" />
    </div>

    <!-- 空状态 — 诗意风格 -->
    <div
      v-if="messages.length === 0 && !loading"
      class="chat-history__empty"
    >
      <AppLogo
        :size="36"
        class="chat-history__empty-icon"
        type="icon"
      />
      <div class="chat-history__empty-content">
        <h3 class="chat-history__empty-title font-decorative">
          想去哪里？
        </h3>
        <p class="chat-history__empty-desc">
          告诉我您想去的地方和时间
        </p>
      </div>
    </div>

    <!-- 消息列表 -->
    <div
      v-for="(msg, idx) in messages"
      :key="msg.id"
    >
      <ChatMessage
        :message="msg"
        :is-latest="idx === messages.length - 1"
      />
    </div>

    <!-- 底部占位 -->
    <div class="chat-history__spacer" />
  </div>
</template>

<style scoped>
.chat-history {
  flex: 1;
  overflow-y: auto;
  padding: var(--space-6);
  display: flex;
  flex-direction: column;
  scroll-behavior: smooth;
}

/* 自定义滚动条 */
.chat-history::-webkit-scrollbar {
  width: 4px;
}
.chat-history::-webkit-scrollbar-thumb {
  background: var(--color-border);
  border-radius: 4px;
}

/* Loading */
.chat-history__loading {
  text-align: center;
  padding: var(--space-8);
}

/* 空状态 */
.chat-history__empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: var(--space-4);
  text-align: center;
}

.chat-history__empty-icon {
  margin-bottom: var(--space-2);
  color: var(--color-brand-500);
  animation: float 3s ease-in-out infinite;
}

@keyframes float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}

.chat-history__empty-title {
  font-size: 22px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0;
}

.chat-history__empty-desc {
  font-size: var(--text-body);
  color: var(--color-text-tertiary);
  margin: 0;
}

/* 底部占位 */
.chat-history__spacer {
  height: var(--space-4);
}
</style>
