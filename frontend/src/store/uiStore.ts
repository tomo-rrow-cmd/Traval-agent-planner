/* ============================================================
   UI 状态管理（含通知系统）
   对应文档：前端界面设计文档.md · §6.2 Store 详细职责
   ============================================================ */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type ToastType = 'success' | 'error' | 'warning' | 'info'
export type Breakpoint = 'xs' | 'sm' | 'md' | 'lg'

export interface Toast {
  id: string
  type: ToastType
  message: string
  description?: string
  duration: number
  action?: {
    label: string
    handler: () => void
  }
  createdAt: number
}

export const useUiStore = defineStore('ui', () => {
  /* ===== State ===== */
  const sidebarCollapsed = ref(false)
  const theme = ref<'light' | 'dark'>('light')
  const globalLoading = ref(false)
  const currentBreakpoint = ref<Breakpoint>('lg')
  const toasts = ref<Toast[]>([])
  const onlineStatus = ref(navigator.onLine)
  const loginModalVisible = ref(false)

  function openLoginModal() { loginModalVisible.value = true }
  function closeLoginModal() { loginModalVisible.value = false }

  let toastCounter = 0

  /* ===== Getters ===== */
  const themeConfig = computed(() => ({
    colorPrimary: '#E8A87C',
    borderRadius: 6,
  }))

  /* ===== Actions ===== */

  function initTheme() {
    const saved = localStorage.getItem('theme')
    if (saved === 'dark' || (!saved && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
      theme.value = 'dark'
      document.documentElement.setAttribute('data-theme', 'dark')
    }
  }

  function setTheme(t: 'light' | 'dark') {
    theme.value = t
    document.documentElement.setAttribute('data-theme', t)
    localStorage.setItem('theme', t)
  }

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  /** 显示通知 */
  function showToast(toast: Omit<Toast, 'id' | 'createdAt'>): string {
    const id = `toast_${++toastCounter}`
    toasts.value.push({
      ...toast,
      id,
      createdAt: Date.now(),
    })

    // 自动关闭（duration 为 0 时不自动关闭）
    if (toast.duration > 0) {
      setTimeout(() => {
        dismissToast(id)
      }, toast.duration)
    }

    return id
  }

  /** 关闭单条通知 */
  function dismissToast(id: string) {
    const index = toasts.value.findIndex((t) => t.id === id)
    if (index !== -1) {
      toasts.value.splice(index, 1)
    }
  }

  /** 关闭所有通知 */
  function dismissAllToasts() {
    toasts.value = []
  }

  /**
   * 便捷方法：显示成功通知
   */
  function showSuccess(message: string, duration = 3000) {
    return showToast({ type: 'success', message, duration })
  }

  /** 显示错误通知 */
  function showError(message: string, action?: { label: string; handler: () => void }) {
    return showToast({ type: 'error', message, duration: 0, action })
  }

  /** 显示警告通知 */
  function showWarning(message: string, duration = 8000) {
    return showToast({ type: 'warning', message, duration })
  }

  /** 设置断点 */
  function setBreakpoint(bp: Breakpoint) {
    currentBreakpoint.value = bp
  }

  return {
    sidebarCollapsed,
    theme,
    globalLoading,
    currentBreakpoint,
    toasts,
    onlineStatus,
    loginModalVisible,
    themeConfig,
    initTheme,
    setTheme,
    toggleSidebar,
    showToast,
    dismissToast,
    dismissAllToasts,
    showSuccess,
    showError,
    showWarning,
    setBreakpoint,
    openLoginModal,
    closeLoginModal,
  }
})
