<script setup lang="ts">
/* ============================================================
   AppSidebar — 导航侧栏（会话列表、方案入口）
   对应文档：前端界面设计文档.md · §2.3
   视觉规范：界面视觉设计系统.md · §15.2
   ============================================================ */

import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useChatStore } from '@/store/chatStore'
import { useUiStore } from '@/store/uiStore'
import { useAuthStore } from '@/store/authStore'
import type { ChatSession } from '@/types/chat'

const router = useRouter()
const route = useRoute()
const chatStore = useChatStore()
const uiStore = useUiStore()
const authStore = useAuthStore()

const isCollapsed = computed(() => uiStore.sidebarCollapsed)

// 三个点菜单 + 重命名状态
const menuSessionId = ref<string | null>(null)
const renamingSessionId = ref<string | null>(null)
const renameValue = ref('')
const renameInputRef = ref<HTMLInputElement | null>(null)

/** 创建新会话 */
async function handleNewChat() {
  const session = await chatStore.createSession('新对话')
  router.push(`/chat/${session.id}`)
}

/** 进入会话 */
function goToSession(sessionId: string) {
  router.push(`/chat/${sessionId}`)
}

function goToPlans() { router.push('/plans') }
function goToTravelogues() { router.push('/travelogues') }
function goToProfile() { router.push('/profile') }

const isActive = (sessionId: string) => route.params.sessionId === sessionId

// ---------- 三个点菜单 ----------
function toggleMenu(e: MouseEvent, sessionId: string) {
  e.stopPropagation()
  menuSessionId.value = menuSessionId.value === sessionId ? null : sessionId
}

function closeMenu() { menuSessionId.value = null }

onMounted(async () => {
  document.addEventListener('click', closeMenu)
  await authStore.initializeSession()
  await chatStore.fetchSessions()
})
const stopIdentityWatch = watch(
  () => authStore.identityRevision,
  async () => {
    await authStore.initializeSession()
    await chatStore.fetchSessions()
  },
)
onUnmounted(() => {
  document.removeEventListener('click', closeMenu)
  stopIdentityWatch()
})

function handlePin(session: ChatSession) {
  chatStore.togglePinSession(session.id, !session.pinned)
  closeMenu()
}

function startRename(e: MouseEvent, session: ChatSession) {
  e.stopPropagation()
  renamingSessionId.value = session.id
  renameValue.value = session.title || ''
  closeMenu()
  nextTick(() => {
    // 找到输入框并聚焦
    const input = document.querySelector('.session-item__rename-input') as HTMLInputElement
    input?.focus()
    input?.select()
  })
}

function confirmRename(sessionId: string) {
  if (renameValue.value.trim()) {
    chatStore.renameSession(sessionId, renameValue.value.trim())
  }
  renamingSessionId.value = null
}

function cancelRename() {
  renamingSessionId.value = null
}

function handleDelete(session: ChatSession) {
  if (!confirm(`确定要删除会话「${session.title || '新对话'}」吗？`)) return
  chatStore.deleteSession(session.id)
  closeMenu()
}

// 排序：置顶的排前面
const sortedSessions = computed(() => {
  return [...chatStore.sessions].sort((a, b) => {
    if (a.pinned && !b.pinned) return -1
    if (!a.pinned && b.pinned) return 1
    return 0
  })
})
const displayedSessions = computed(() => (
  chatStore.sessionsLoading || chatStore.sessionsError
    ? []
    : sortedSessions.value.slice(0, 20)
))
</script>

<template>
  <aside
    class="app-sidebar"
    :class="{ 'app-sidebar--collapsed': isCollapsed }"
  >
    <!-- 新会话按钮 -->
    <div class="app-sidebar__new-chat">
      <button
        class="new-chat-btn"
        :class="{ 'new-chat-btn--collapsed': isCollapsed }"
        @click="handleNewChat"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <line
            x1="12"
            y1="5"
            x2="12"
            y2="19"
          /><line
            x1="5"
            y1="12"
            x2="19"
            y2="12"
          />
        </svg>
        <span v-if="!isCollapsed">新对话</span>
      </button>
    </div>

    <!-- 会话列表 -->
    <div
      v-if="!isCollapsed"
      class="app-sidebar__sessions"
    >
      <div class="app-sidebar__section-label">
        最近会话
      </div>
      <div
        v-if="chatStore.sessionsLoading"
        class="app-sidebar__sessions-state"
      >
        正在加载会话…
      </div>
      <button
        v-else-if="chatStore.sessionsError"
        class="app-sidebar__sessions-retry"
        @click="chatStore.fetchSessions()"
      >
        加载失败，点击重试
      </button>
      <div
        v-else-if="sortedSessions.length === 0"
        class="app-sidebar__sessions-state"
      >
        暂无历史会话
      </div>
      <div
        v-for="session in displayedSessions"
        :key="session.id"
        class="session-item"
        :class="{
          'session-item--active': isActive(session.id),
          'session-item--pinned': session.pinned,
        }"
        @click="goToSession(session.id)"
      >
        <svg
          class="session-item__icon"
          width="16"
          height="16"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
        </svg>

        <!-- 重命名输入 -->
        <div
          v-if="renamingSessionId === session.id"
          class="session-item__rename"
          @click.stop
        >
          <input
            ref="renameInputRef"
            v-model="renameValue"
            class="session-item__rename-input"
            maxlength="50"
            placeholder="输入新名称"
            @keydown.enter="confirmRename(session.id)"
            @keydown.escape="cancelRename"
            @blur="confirmRename(session.id)"
          >
        </div>

        <!-- 常规显示 -->
        <div
          v-else
          class="session-item__info"
        >
          <div class="session-item__title truncate">
            <svg
              v-if="session.pinned"
              class="session-item__pin-icon"
              width="12"
              height="12"
              viewBox="0 0 24 24"
              fill="currentColor"
            ><path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z" /></svg>
            {{ session.title || '新对话' }}
          </div>
          <div
            v-if="session.last_message_preview"
            class="session-item__preview truncate"
          >
            {{ session.last_message_preview }}
          </div>
        </div>

        <!-- 三个点按钮 -->
        <button
          v-if="renamingSessionId !== session.id"
          class="session-item__menu-btn"
          :class="{ 'session-item__menu-btn--open': menuSessionId === session.id }"
          @click.stop="toggleMenu($event, session.id)"
        >
          <svg
            width="14"
            height="14"
            viewBox="0 0 24 24"
            fill="currentColor"
          ><circle
            cx="5"
            cy="12"
            r="2"
          /><circle
            cx="12"
            cy="12"
            r="2"
          /><circle
            cx="19"
            cy="12"
            r="2"
          /></svg>
        </button>

        <!-- 下拉菜单（内联绝对定位） -->
        <div
          v-if="menuSessionId === session.id"
          class="session-menu"
          @click.stop
        >
          <button
            class="session-menu__item"
            @click="handlePin(session)"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            ><path d="M16 12V4h1V2H7v2h1v8l-2 2v2h5.2v6h1.6v-6H18v-2l-2-2z" /></svg>
            <span>{{ session.pinned ? '取消置顶' : '置顶' }}</span>
          </button>
          <button
            class="session-menu__item"
            @click.stop="startRename($event, session)"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            ><path d="M17 3a2.828 2.828 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5L17 3z" /></svg>
            <span>重命名</span>
          </button>
          <div class="session-menu__divider" />
          <button
            class="session-menu__item session-menu__item--danger"
            @click="handleDelete(session)"
          >
            <svg
              width="16"
              height="16"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              stroke-width="2"
              stroke-linecap="round"
            ><polyline points="3 6 5 6 21 6" /><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" /></svg>
            <span>删除</span>
          </button>
        </div>
      </div>

      <div
        v-if="chatStore.sessions.length === 0"
        class="app-sidebar__empty"
      >
        暂无会话，开始一段新的旅行规划吧
      </div>
    </div>

    <!-- 底部菜单 -->
    <div class="app-sidebar__footer">
      <button
        class="sidebar-footer-btn"
        @click="goToPlans"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        ><rect
          x="3"
          y="4"
          width="18"
          height="18"
          rx="2"
          ry="2"
        /><line
          x1="16"
          y1="2"
          x2="16"
          y2="6"
        /><line
          x1="8"
          y1="2"
          x2="8"
          y2="6"
        /><line
          x1="3"
          y1="10"
          x2="21"
          y2="10"
        /></svg>
        <span v-if="!isCollapsed">我的方案</span>
      </button>
      <button
        class="sidebar-footer-btn"
        @click="goToTravelogues"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        ><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" /><polyline points="14 2 14 8 20 8" /><line
          x1="16"
          y1="13"
          x2="8"
          y2="13"
        /><line
          x1="16"
          y1="17"
          x2="8"
          y2="17"
        /><polyline points="10 9 9 9 8 9" /></svg>
        <span v-if="!isCollapsed">游记</span>
      </button>
      <button
        class="sidebar-footer-btn"
        @click="goToProfile"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        ><circle
          cx="12"
          cy="8"
          r="4"
        /><path d="M20 21a8 8 0 1 0-16 0" /></svg>
        <span v-if="!isCollapsed">个人中心</span>
      </button>
      <button
        v-if="isCollapsed"
        class="sidebar-footer-btn"
        title="新对话"
        @click="handleNewChat"
      >
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        ><line
          x1="12"
          y1="5"
          x2="12"
          y2="19"
        /><line
          x1="5"
          y1="12"
          x2="19"
          y2="12"
        /></svg>
      </button>
    </div>
  </aside>
</template>

<style scoped>
.app-sidebar {
  width: var(--sidebar-width);
  min-width: var(--sidebar-width);
  height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--color-bg-secondary);
  border-right: 1px solid var(--color-border);
  transition: width var(--dur-slide) var(--ease-out-expo), min-width var(--dur-slide) var(--ease-out-expo);
  overflow: hidden;
}
.app-sidebar--collapsed {
  width: var(--sidebar-collapsed-width);
  min-width: var(--sidebar-collapsed-width);
}

/* 新会话按钮 */
.app-sidebar__new-chat { padding: var(--space-4); flex-shrink: 0; }
.new-chat-btn {
  width: 100%; display: flex; align-items: center; justify-content: center;
  gap: var(--space-2); height: 40px;
  border: 2px dashed var(--color-brand-300); background: transparent;
  color: var(--color-brand-600); font-size: var(--text-body-sm);
  font-weight: var(--fw-medium); border-radius: var(--radius-sm);
  cursor: pointer; transition: all var(--dur-fast) var(--ease-in-out);
}
.new-chat-btn:hover {
  background: var(--color-brand-50); border-color: var(--color-brand-500);
  color: var(--color-brand-700);
}
.new-chat-btn--collapsed {
  padding: 0; width: 40px; margin: 0 auto;
  border-style: solid; border-color: var(--color-border);
}

/* 会话列表 */
.app-sidebar__sessions { flex: 1; overflow-y: auto; padding: 0 var(--space-3); }
.app-sidebar__section-label {
  padding: var(--space-2) var(--space-2) var(--space-1);
  font-size: var(--text-small); color: var(--color-text-tertiary);
  font-weight: var(--fw-medium); text-transform: uppercase; letter-spacing: 0.5px;
}

.app-sidebar__sessions-state,
.app-sidebar__sessions-retry {
  width: 100%;
  padding: var(--space-3);
  color: var(--color-text-tertiary);
  font-size: var(--text-small);
  text-align: left;
}

.app-sidebar__sessions-retry {
  border: 0;
  background: transparent;
  cursor: pointer;
}

.app-sidebar__sessions-retry:hover {
  color: var(--color-brand-600);
}

.session-item {
  display: flex; align-items: center; gap: var(--space-2);
  padding: var(--space-2) var(--space-2);
  border-radius: var(--radius-sm); cursor: pointer;
  transition: all var(--dur-fast) var(--ease-in-out);
  margin-bottom: 2px; position: relative;
}
.session-item:hover { background: var(--color-brand-50); }
.session-item--active {
  background: var(--color-brand-50); border-left: 3px solid var(--color-brand-500);
}
.session-item--pinned { background: var(--color-brand-50); }

.session-item__icon { flex-shrink: 0; color: var(--color-text-tertiary); }
.session-item--active .session-item__icon { color: var(--color-brand-500); }

.session-item__info { flex: 1; min-width: 0; }
.session-item__title {
  display: flex; align-items: center; gap: 4px;
  font-size: var(--text-body-sm); color: var(--color-text-primary);
  font-weight: var(--fw-medium);
}
.session-item--active .session-item__title { color: var(--color-brand-700); }
.session-item__pin-icon { flex-shrink: 0; color: var(--color-brand-500); }
.session-item__preview {
  font-size: var(--text-small); color: var(--color-text-tertiary); margin-top: 1px;
}

/* 三个点按钮 */
.session-item__menu-btn {
  flex-shrink: 0; width: 24px; height: 24px;
  border: none; background: transparent; color: var(--color-text-tertiary);
  cursor: pointer; border-radius: 4px;
  display: flex; align-items: center; justify-content: center;
  opacity: 0; transition: all var(--dur-fast) var(--ease-in-out);
}
.session-item:hover .session-item__menu-btn { opacity: 1; }
.session-item__menu-btn:hover,
.session-item__menu-btn--open {
  background: var(--color-bg-tertiary); color: var(--color-text-primary); opacity: 1;
}

/* 重命名输入 */
.session-item__rename { flex: 1; min-width: 0; }
.session-item__rename-input {
  width: 100%; border: 1.5px solid var(--color-brand-400);
  border-radius: 4px; padding: 2px 6px;
  font-size: var(--text-body-sm); color: var(--color-text-primary);
  background: var(--color-bg-card); outline: none; font-family: inherit;
}

/* 空状态 */
.app-sidebar__empty {
  padding: var(--space-8) var(--space-4); text-align: center;
  font-size: var(--text-body-sm); color: var(--color-text-tertiary);
  line-height: var(--lh-relaxed);
}

/* 底部菜单 */
.app-sidebar__footer {
  flex-shrink: 0; padding: var(--space-3);
  border-top: 1px solid var(--color-border); display: flex; flex-direction: column; gap: 2px;
}
.sidebar-footer-btn {
  display: flex; align-items: center; gap: var(--space-3);
  padding: var(--space-2) var(--space-3); border: none; background: transparent;
  color: var(--color-text-secondary); font-size: var(--text-body-sm);
  border-radius: var(--radius-sm); cursor: pointer;
  transition: all var(--dur-fast) var(--ease-in-out);
}
.sidebar-footer-btn:hover { background: var(--color-bg-tertiary); color: var(--color-text-primary); }

/* ========== 下拉菜单（绝对定位） ========== */
.session-menu {
  position: absolute;
  right: 4px;
  top: 100%;
  z-index: 100;
  min-width: 140px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-dropdown);
  padding: var(--space-1);
  animation: menuFadeIn 0.15s var(--ease-out-expo);
}
@keyframes menuFadeIn {
  from { opacity: 0; transform: translateY(-4px) scale(0.96); }
  to { opacity: 1; transform: translateY(0) scale(1); }
}

.session-menu__item {
  display: flex; align-items: center; gap: var(--space-2);
  width: 100%; padding: var(--space-2) var(--space-3);
  border: none; background: transparent;
  font-size: var(--text-body-sm); color: var(--color-text-primary);
  cursor: pointer; border-radius: var(--radius-sm);
  transition: all var(--dur-fast) var(--ease-in-out);
  font-family: inherit; white-space: nowrap;
}
.session-menu__item:hover { background: var(--color-brand-50); color: var(--color-brand-700); }
.session-menu__item svg { flex-shrink: 0; color: var(--color-text-tertiary); }
.session-menu__item:hover svg { color: var(--color-brand-500); }

.session-menu__item--danger { color: var(--color-error); }
.session-menu__item--danger:hover { background: #FFF1F0; color: var(--color-error); }
.session-menu__item--danger:hover svg { color: var(--color-error); }

.session-menu__divider {
  height: 1px; background: var(--color-border-light);
  margin: var(--space-1) var(--space-1);
}
</style>
