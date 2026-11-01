import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/store/authStore'

vi.mock('@/api/auth', () => ({
  sendSmsCode: vi.fn(),
  login: vi.fn(),
  loginWithPhone: vi.fn(),
  register: vi.fn(),
  logout: vi.fn(),
}))

vi.mock('@/api/user', () => ({
  mergeAnonymousData: vi.fn(),
}))

import { loginWithPhone as apiLogin, register as apiRegister, logout as apiLogout } from '@/api/auth'
import { mergeAnonymousData as apiMergeAnonymous } from '@/api/user'
import { mockLoginResponse, mockToken, mockUser, mockAnonymousMergeResponse } from '@/test/mocks/auth'

describe('authStore 数据流', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  describe('Token 管理', () => {
    it('登录后应正确存储 accessToken 和 refreshToken', async () => {
      const store = useAuthStore()
      vi.mocked(apiLogin).mockResolvedValue({ data: mockLoginResponse } as any)
      vi.mocked(apiMergeAnonymous).mockResolvedValue({ data: mockAnonymousMergeResponse } as any)

      await store.login('13800138000', '123456')

      expect(store.accessToken).toBe(mockToken.access_token)
      expect(store.refreshToken).toBe(mockToken.refresh_token)
      expect(store.expiresIn).toBe(3600)
      expect(store.isLoggedIn).toBe(true)
      expect(localStorage.getItem('access_token')).toBe(mockToken.access_token)
    })

    it('登录后应正确设置用户信息', async () => {
      const store = useAuthStore()
      vi.mocked(apiLogin).mockResolvedValue({ data: mockLoginResponse } as any)
      vi.mocked(apiMergeAnonymous).mockResolvedValue({ data: mockAnonymousMergeResponse } as any)

      await store.login('13800138000', '123456')

      expect(store.user).toEqual(mockUser)
      expect(store.user?.nickname).toBe('旅行者Mock')
    })

    it('登出后应清除所有认证状态', async () => {
      const store = useAuthStore()
      vi.mocked(apiLogin).mockResolvedValue({ data: mockLoginResponse } as any)
      vi.mocked(apiMergeAnonymous).mockResolvedValue({ data: mockAnonymousMergeResponse } as any)
      vi.mocked(apiLogout).mockResolvedValue({ data: { code: 0, message: '', data: {} } } as any)

      await store.login('13800138000', '123456')
      expect(store.isLoggedIn).toBe(true)

      await store.logout()

      expect(store.accessToken).toBeNull()
      expect(store.refreshToken).toBeNull()
      expect(store.user).toBeNull()
      expect(store.isLoggedIn).toBe(false)
      expect(localStorage.getItem('access_token')).toBeNull()
    })
  })

  describe('会话恢复', () => {
    it('应从 localStorage 恢复令牌', () => {
      localStorage.setItem('access_token', mockToken.access_token)
      localStorage.setItem('refresh_token', mockToken.refresh_token)
      localStorage.setItem('expires_in', '3600')

      const store = useAuthStore()
      store.restoreSession()

      expect(store.accessToken).toBe(mockToken.access_token)
      // restoreSession 只恢复 token, user 需通过 /auth/sessions 重新获取
      expect(store.isLoggedIn).toBe(true)
    })

    it('空 localStorage 时恢复后状态应为未登录', () => {
      const store = useAuthStore()
      store.restoreSession()

      expect(store.isLoggedIn).toBe(false)
      expect(store.accessToken).toBeNull()
      expect(store.user).toBeNull()
    })
  })

  describe('匿名会话', () => {
    it('应创建匿名会话 ID 并存入 localStorage', () => {
      const store = useAuthStore()
      store.createAnonymousSession()

      expect(store.anonymousSessionId).toBeTruthy()
      expect(store.anonymousSessionId).toMatch(/^sess_anonymous_/)
      expect(store.isAnonymous).toBe(true)
      expect(localStorage.getItem('anonymous_session_id')).toBe(store.anonymousSessionId)
    })

    it('重复创建时应复用同一个匿名会话 ID', () => {
      const store = useAuthStore()
      const first = store.createAnonymousSession()
      const second = store.createAnonymousSession()

      expect(second).toBe(first)
      expect(localStorage.getItem('anonymous_session_id')).toBe(first)
    })

    it('登录后匿名数据应被合并并清除', async () => {
      const store = useAuthStore()
      vi.mocked(apiLogin).mockResolvedValue({ data: mockLoginResponse } as any)
      vi.mocked(apiMergeAnonymous).mockResolvedValue({ data: mockAnonymousMergeResponse } as any)

      store.createAnonymousSession()
      const anonId = store.anonymousSessionId

      await store.login('13800138000', '123456')

      expect(apiMergeAnonymous).toHaveBeenCalledWith({ anonymous_session_id: anonId })
      expect(store.anonymousSessionId).toBeNull()
      expect(store.isAnonymous).toBe(false)
    })
  })

  describe('注册流程', () => {
    it('注册后应自动登录', async () => {
      const store = useAuthStore()
      vi.mocked(apiRegister).mockResolvedValue({ data: mockLoginResponse } as any)
      vi.mocked(apiMergeAnonymous).mockResolvedValue({ data: mockAnonymousMergeResponse } as any)

      await store.register('13800138000', 'password123', '新用户')

      expect(store.accessToken).toBe(mockToken.access_token)
      expect(store.isLoggedIn).toBe(true)
      expect(store.user?.nickname).toBe('旅行者Mock')
    })
  })
})
