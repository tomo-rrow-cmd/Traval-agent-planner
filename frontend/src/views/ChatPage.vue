<script setup lang="ts">
import { useRouter } from 'vue-router'
import AppLogo from "@/components/brand/AppLogo.vue"
import { useChatStore } from '@/store/chatStore'

const router = useRouter()
const chatStore = useChatStore()

async function startNewChat() {
  const session = await chatStore.createSession()
  router.push(`/chat/${session.id}`)
}
</script>

<template>
  <div class="chat-page">
    <div class="chat-page__welcome">
      <AppLogo
        :size="64"
        class="chat-page__icon"
      />
      <h1 class="chat-page__title">
        开始您的旅行规划
      </h1>
      <p class="chat-page__desc">
        告诉我您想去哪里、玩几天，AI 将为您生成完整的旅行方案
      </p>
      <a-button
        type="primary"
        size="large"
        class="chat-page__start-btn"
        @click="startNewChat"
      >
        开始新对话
      </a-button>
    </div>
  </div>
</template>

<style scoped>
.chat-page {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: var(--space-8);
}

.chat-page__welcome {
  text-align: center;
  max-width: 480px;
}

.chat-page__icon {
  margin-bottom: var(--space-4);
  color: var(--color-brand-500);
}

.chat-page__title {
  font-size: var(--text-h1);
  font-weight: var(--fw-bold);
  color: var(--color-text-primary);
  margin-bottom: var(--space-3);
}

.chat-page__desc {
  font-size: var(--text-body-lg);
  color: var(--color-text-tertiary);
  line-height: var(--lh-relaxed);
  margin-bottom: var(--space-8);
}

.chat-page__start-btn {
  height: 48px;
  padding: 0 32px;
  font-size: var(--text-body-lg);
  border-radius: var(--radius-sm);
}
</style>
