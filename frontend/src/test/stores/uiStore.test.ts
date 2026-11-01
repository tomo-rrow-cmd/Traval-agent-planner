import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useUiStore } from '@/store/uiStore'

describe('uiStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    localStorage.clear()
  })

  describe('theme', () => {
    it('默认浅色主题', () => {
      const store = useUiStore()
      expect(store.theme).toBe('light')
    })

    it('setTheme 切换并持久化', () => {
      const store = useUiStore()
      store.setTheme('dark')
      expect(store.theme).toBe('dark')
      expect(localStorage.getItem('theme')).toBe('dark')
    })

    it('initTheme 从 localStorage 恢复', () => {
      localStorage.setItem('theme', 'dark')
      const store = useUiStore()
      store.initTheme()
      expect(store.theme).toBe('dark')
    })
  })

  describe('sidebar', () => {
    it('toggleSidebar 切换折叠状态', () => {
      const store = useUiStore()
      expect(store.sidebarCollapsed).toBe(false)
      store.toggleSidebar()
      expect(store.sidebarCollapsed).toBe(true)
    })
  })

  describe('toasts', () => {
    it('showToast 添加通知', () => {
      const store = useUiStore()
      const id = store.showToast({ type: 'success', message: '操作成功', duration: 3000 })
      expect(store.toasts).toHaveLength(1)
      expect(store.toasts[0].message).toBe('操作成功')
      expect(typeof id).toBe('string')
    })

    it('dismissToast 移除通知', () => {
      const store = useUiStore()
      const id = store.showToast({ type: 'info', message: 'test', duration: 0 })
      store.dismissToast(id)
      expect(store.toasts).toHaveLength(0)
    })

    it('dismissAllToasts 清空全部', () => {
      const store = useUiStore()
      store.showToast({ type: 'info', message: 'a', duration: 0 })
      store.showToast({ type: 'info', message: 'b', duration: 0 })
      store.dismissAllToasts()
      expect(store.toasts).toHaveLength(0)
    })

    it('showSuccess 便捷方法', () => {
      const store = useUiStore()
      store.showSuccess('成功')
      expect(store.toasts[0].type).toBe('success')
      expect(store.toasts[0].duration).toBe(3000)
    })

    it('showError 带 action 且不自动关闭', () => {
      const handler = vi.fn()
      const store = useUiStore()
      store.showError('失败', { label: '重试', handler })
      expect(store.toasts[0].type).toBe('error')
      expect(store.toasts[0].duration).toBe(0)
      expect(store.toasts[0].action?.label).toBe('重试')
    })

    it('showWarning 默认 8 秒', () => {
      const store = useUiStore()
      store.showWarning('警告')
      expect(store.toasts[0].duration).toBe(8000)
    })
  })

  describe('modal', () => {
    it('openLoginModal / closeLoginModal', () => {
      const store = useUiStore()
      expect(store.loginModalVisible).toBe(false)
      store.openLoginModal()
      expect(store.loginModalVisible).toBe(true)
      store.closeLoginModal()
      expect(store.loginModalVisible).toBe(false)
    })
  })

  describe('breakpoint', () => {
    it('setBreakpoint', () => {
      const store = useUiStore()
      store.setBreakpoint('sm')
      expect(store.currentBreakpoint).toBe('sm')
    })
  })

  describe('loading', () => {
    it('globalLoading 默认 false', () => {
      const store = useUiStore()
      expect(store.globalLoading).toBe(false)
      store.globalLoading = true
      expect(store.globalLoading).toBe(true)
    })
  })
})
