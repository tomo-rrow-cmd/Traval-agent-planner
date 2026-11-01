<script setup lang="ts">
/* ============================================================
   ChatMessage — 装饰风格聊天气泡
   设计灵感：Layla.ai 的朋友感 + 小地球旅行的诗意温暖
   ============================================================ */

import { computed } from 'vue'
import MarkdownIt from 'markdown-it'
import type { MessageRecord } from '@/types/chat'
import AppLogo from '@/components/brand/AppLogo.vue'
import { useRouter } from 'vue-router'

const md = new MarkdownIt({ html: false, breaks: true, linkify: true })

const props = defineProps<{
  message: MessageRecord
  isLatest?: boolean
}>()

const router = useRouter()

const isUser = props.message.role === 'user'
const isAssistant = props.message.role === 'assistant'
const isPlanProgress = props.message.message_type === 'plan_progress'
const isPlanResult = props.message.message_type === 'plan_result'

const renderedContent = computed(() => {
  return md.render(props.message.content)
})

const planId = computed(() => {
  return (props.message.metadata?.plan_id as string) ?? ''
})

const progressPercent = computed(() => {
  return (props.message.metadata?.percent as number) ?? 0
})

function goToPlan() {
  if (planId.value) {
    router.push(`/plans/${planId.value}`)
  }
}
</script>

<template>
  <div
    class="chat-message"
    :class="{
      'chat-message--user': isUser,
      'chat-message--assistant': isAssistant,
      'chat-message--latest': isLatest,
    }"
  >
    <!-- AI 头像带渐变背景 -->
    <div
      v-if="isAssistant"
      class="chat-message__avatar"
    >
      <AppLogo
        :size="20"
        class="chat-message__avatar-icon"
      />
    </div>

    <div class="chat-message__body">
      <!-- AI 名称标签 -->
      <div
        v-if="isAssistant"
        class="chat-message__sender"
      >
        <span class="chat-message__sender-name">旅行者</span>
      </div>

      <!-- 消息气泡 -->
      <div class="chat-message__bubble">
        <!-- plan_progress 类型：进度条卡片 -->
        <div
          v-if="isPlanProgress"
          class="chat-message__progress"
        >
          <div class="chat-message__progress-header">
            <span class="chat-message__progress-dot" />
            <span class="chat-message__progress-label">{{ message.content }}</span>
          </div>
          <a-progress
            :percent="progressPercent"
            :show-info="false"
            :stroke-color="{
              '0%': '#E8A87C',
              '100%': '#D49366',
            }"
            size="small"
          />
        </div>

        <!-- plan_result 类型：方案结果（Markdown 渲染） -->
        <div
          v-else-if="isPlanResult"
          class="chat-message__result"
        >
          <div class="chat-message__content">
            <!-- eslint-disable vue/no-v-html -->
            <div
              class="chat-message__markdown chat-message__markdown-plan"
              v-html="renderedContent"
            />
            <!-- eslint-enable vue/no-v-html -->
          </div>
          <a-button
            v-if="planId"
            type="primary"
            size="small"
            class="chat-message__result-btn"
            @click="goToPlan"
          >
            查看完整方案 →
          </a-button>
        </div>

        <!-- 普通文本（AI 用 Markdown 渲染，用户保持纯文本） -->
        <div
          v-else
          class="chat-message__content"
        >
          <!-- eslint-disable vue/no-v-html -->
          <div
            v-if="isAssistant"
            class="chat-message__markdown"
            v-html="renderedContent"
          />
          <!-- eslint-enable vue/no-v-html -->
          <template v-else>
            {{ message.content }}
          </template>
        </div>
      </div>
    </div>

    <!-- 用户头像 -->
    <div
      v-if="isUser"
      class="chat-message__avatar chat-message__avatar--user"
    >
      <span class="chat-message__avatar-text">我</span>
    </div>
  </div>
</template>

<style scoped>
.chat-message {
  display: flex;
  gap: var(--space-3);
  margin-bottom: var(--space-2);
  animation: messageIn 0.3s var(--ease-out-expo);
}

@keyframes messageIn {
  from { opacity: 0; transform: translateY(8px); }
  to { opacity: 1; transform: translateY(0); }
}

.chat-message--user {
  flex-direction: row;
  justify-content: flex-end;
}

.chat-message--assistant {
  justify-content: flex-start;
}

/* ===== Avatar ===== */
.chat-message__avatar {
  width: 40px;
  height: 40px;
  border-radius: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: var(--text-small);
  font-weight: var(--fw-bold);
  box-shadow: 0 4px 12px rgba(232, 168, 124, 0.15);
}

.chat-message--assistant .chat-message__avatar {
  background: var(--gradient-gold);
  color: white;
}

.chat-message--user .chat-message__avatar {
  background: var(--gradient-ocean);
  color: white;
  box-shadow: 0 4px 12px rgba(126, 184, 218, 0.2);
}

.chat-message__avatar-icon {
  display: flex;
  align-items: center;
  justify-content: center;
}

.chat-message__avatar-text {
  font-size: 14px;
}

/* ===== Body ===== */
.chat-message__body {
  max-width: 65%;
  min-width: 0;
}

.chat-message--user .chat-message__body {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
}

/* ===== Sender Label ===== */
.chat-message__sender {
  display: flex;
  align-items: center;
  gap: var(--space-1);
  margin-bottom: var(--space-1);
  padding-left: var(--space-1);
}

.chat-message__sender-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-brand-600);
}

/* ===== Bubble ===== */
.chat-message__bubble {
  padding: var(--space-2) var(--space-3);
  position: relative;
  line-height: 1.5;
}

/* AI 气泡 — 手账风格 */
.chat-message--assistant .chat-message__bubble {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 4px 16px 16px 16px;
  position: relative;
  box-shadow: 0 2px 8px rgba(139, 115, 85, 0.06);
  padding-bottom: var(--space-3);
}

/* AI 气泡左边装饰线 */
.chat-message--assistant .chat-message__bubble::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--gradient-gold);
  border-radius: 3px 0 0 3px;
}

/* 用户气泡 — 纯杏色 */
.chat-message--user .chat-message__bubble {
  background: var(--color-brand-500);
  color: white;
  border-radius: 16px 4px 16px 16px;
  box-shadow: 0 4px 16px rgba(232, 168, 124, 0.2);
}

/* 公众号风格的引用效果 — 收起时最后一条消息 */
.chat-message--latest.chat-message--assistant .chat-message__bubble::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 12px;
  width: 8px;
  height: 8px;
  background: var(--color-bg-card);
  border-right: 1px solid var(--color-border);
  border-bottom: 1px solid var(--color-border);
  transform: rotate(-45deg);
}

/* ===== Content ===== */
.chat-message__content {
  font-size: var(--text-body);
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-word;
}
.chat-message__content > *:last-child {
  margin-bottom: 0;
}

.chat-message--user .chat-message__content {
  font-weight: 450;
}

/* ===== 进度条卡片 ===== */
.chat-message__progress {
  padding: var(--space-2) 0;
}
.chat-message__progress-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
  margin-bottom: var(--space-2);
}
.chat-message__progress-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--color-brand-500);
  animation: pulse 1.5s ease infinite;
  flex-shrink: 0;
}
@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}
.chat-message__progress-label {
  font-size: var(--text-body-sm);
  color: var(--color-brand-700);
  font-weight: var(--fw-medium);
}

/* ===== 方案结果卡片 ===== */
.chat-message__result {
  text-align: left;
  padding: var(--space-3) 0;
}
.chat-message__result .chat-message__markdown {
  padding: 0;
}
.chat-message__result-btn {
  border-radius: var(--radius-sm);
}
.chat-message__result-footer {
  text-align: center;
  padding-top: var(--space-4);
  margin-top: var(--space-2);
  border-top: 1px solid var(--color-border-light);
}

/* 最大宽度自适应 */
@media (max-width: 768px) {
  .chat-message__body {
    max-width: 80%;
  }
}
</style>
<style>
/* markdown 由 v-html 注入，scoped 选不中，故放全局样式 */
/* 紧凑排版 */
.chat-message__markdown {
  font-size: var(--text-body);
  line-height: 1.45;
}
.chat-message__markdown p {
  margin: 0 0 0.15em;
  line-height: 1.45;
}
.chat-message__markdown p:last-child {
  margin-bottom: 0;
}
.chat-message__markdown > *:last-child {
  margin-bottom: 0 !important;
}
.chat-message__markdown > *:first-child {
  margin-top: 0;
}
.chat-message__markdown strong {
  font-weight: 600;
  color: var(--color-brand-700);
}
.chat-message__markdown em {
  font-style: italic;
}
.chat-message__markdown ul,
.chat-message__markdown ol {
  padding-left: 1.5em;
  margin: 0.1em 0;
}
.chat-message__markdown li {
  margin-bottom: 0.05em;
  line-height: 1.45;
}
.chat-message__markdown a {
  color: var(--color-brand-500);
  text-decoration: underline;
}
.chat-message__markdown code {
  background: var(--color-type-food-bg);
  color: var(--color-brand-600);
  border-radius: 4px;
  padding: 1px 8px;
  font-size: 12px;
  font-style: normal;
  white-space: nowrap;
}
.chat-message__markdown pre {
  background: var(--color-bg-secondary);
  border-radius: var(--radius-sm);
  padding: var(--space-2);
  overflow-x: auto;
  margin: 0.1em 0;
}
.chat-message__markdown pre code {
  background: none;
  padding: 0;
}

/* ===== 标题与分割线 ===== */
.chat-message__markdown h1 {
  font-size: 18px;
  font-weight: 700;
  color: var(--color-brand-700);
  margin: 0.25em 0 0.1em;
  padding-bottom: 0.1em;
  border-bottom: 2px solid var(--color-brand-100);
  line-height: 1.3;
}
.chat-message__markdown h1:first-child {
  margin-top: 0;
}
.chat-message__markdown h2 {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-brand-600);
  margin: 0.15em 0 0.05em;
  padding: 0.05em 0 0.05em 0.4em;
  border-left: 3px solid var(--color-brand-300);
  line-height: 1.3;
}
.chat-message__markdown h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0.1em 0 0.03em;
  line-height: 1.3;
}
.chat-message__markdown hr {
  border: none;
  border-top: 1px solid var(--color-border-light);
  margin: 0.15em 0;
}
.chat-message__markdown table {
  width: 100%;
  border-collapse: collapse;
  font-size: var(--text-small);
  margin: 0.25em 0;
}
.chat-message__markdown th,
.chat-message__markdown td {
  border: 1px solid var(--color-border);
  padding: 0.2em 0.4em;
  text-align: left;
}
.chat-message__markdown th {
  background: var(--color-brand-50);
  font-weight: var(--fw-semibold);
  color: var(--color-brand-700);
}
.chat-message__markdown td {
  background: var(--color-bg-card);
}
.chat-message__markdown tr:nth-child(even) td {
  background: var(--color-bg-secondary);
}
.chat-message__markdown blockquote {
  margin: 0.15em 0;
  padding: 0.1em 0.6em;
  border-left: 3px solid var(--color-brand-300);
  background: var(--color-brand-50);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  color: var(--color-text-secondary);
  font-size: 12px;
  line-height: 1.4;
}
.chat-message__markdown blockquote p {
  margin: 0.05em 0;
}

/* ===== 表格 ===== */
.chat-message__markdown table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
  margin: 0.2em 0;
  border-radius: 6px;
  overflow: hidden;
}
.chat-message__markdown th,
.chat-message__markdown td {
  border: 1px solid var(--color-border);
  padding: 3px 6px;
  text-align: left;
  line-height: 1.4;
  font-size: 12px;
}
.chat-message__markdown th {
  background: var(--color-brand-50);
  font-weight: 600;
  color: var(--color-brand-700);
}
.chat-message__markdown td {
  background: var(--color-bg-card);
}
.chat-message__markdown tr:hover td {
  background: var(--color-brand-50);
}
.chat-message__markdown tr:nth-child(even) td {
  background: var(--color-bg-secondary);
}
.chat-message__markdown tr:nth-child(even):hover td {
  background: var(--color-brand-50);
}

/* ===== 方案结果专属排版 ===== */
.chat-message__markdown-plan {
  font-size: 14px;
  line-height: 1.55;
}
/* h1: 方案标题 */
.chat-message__markdown-plan h1 {
  font-size: 17px;
  font-weight: 700;
  color: var(--color-brand-700);
  margin: 0 0 6px;
  padding: 0 0 6px;
  border-bottom: 2px solid var(--color-brand-100);
  line-height: 1.3;
}
/* h2: 每日行程标题 */
.chat-message__markdown-plan h2 {
  font-size: 15px;
  font-weight: 700;
  color: var(--color-brand-600);
  margin: 14px 0 6px;
  padding: 0 0 2px 8px;
  border-left: 3px solid var(--color-brand-400);
  line-height: 1.3;
}
/* h3: 景点名称 */
.chat-message__markdown-plan h3 {
  font-size: 14px;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 8px 0 2px;
  line-height: 1.3;
}
/* 分隔线隐藏 */
.chat-message__markdown-plan hr {
  display: none;
}
/* 引用块：景点描述 */
.chat-message__markdown-plan blockquote {
  margin: 2px 0;
  padding: 2px 8px;
  border-left: 3px solid var(--color-brand-200);
  background: transparent;
  color: var(--color-text-secondary);
  font-size: 13px;
  line-height: 1.45;
}
.chat-message__markdown-plan blockquote p {
  margin: 0;
}
/* 代码标签：时长/费用 */
.chat-message__markdown-plan code {
  background: #fef3e7;
  color: #d49366;
  border-radius: 4px;
  padding: 1px 8px;
  font-size: 12px;
  font-style: normal;
  white-space: nowrap;
}
/* 段落间距 */
.chat-message__markdown-plan p {
  margin: 4px 0;
  line-height: 1.5;
}
/* 列表：餐饮/交通等 */
.chat-message__markdown-plan ul {
  padding-left: 18px;
  margin: 4px 0;
}
.chat-message__markdown-plan li {
  margin-bottom: 2px;
  font-size: 13px;
  line-height: 1.5;
}
.chat-message__markdown-plan li strong {
  color: var(--color-brand-600);
}
/* 标题后的直接段落缩进 */
.chat-message__markdown-plan h2 + p,
.chat-message__markdown-plan h3 + p {
  margin-top: 0;
}
/* 表格 */
.chat-message__markdown-plan table {
  font-size: 12px;
  margin: 6px 0;
}
.chat-message__markdown-plan th,
.chat-message__markdown-plan td {
  padding: 3px 6px;
  font-size: 12px;
  line-height: 1.4;
}
/* "餐饮"标签 */
.chat-message__markdown-plan p:has(strong:only-child) {
  font-weight: 600;
  color: var(--color-brand-600);
  font-size: 13px;
  margin: 6px 0 2px;
}

</style>
