/* ============================================================
   认证状态管理
   对应文档：前端界面设计文档.md · §6.2 Store 详细职责
   ============================================================ */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { UserProfile } from '@/types/auth'
import { loginWithPhone as apiLogin, logout as apiLogout, sendSmsCode as apiSendSms, register as apiRegister } from '@/api/auth'
import { mergeAnonymousData as apiMerge } from '@/api/user'

export const useAuthStore = defineStore('auth', () => {
  /* ===== State ===== */
  const user = ref<UserProfile | null>(null)
  const accessToken = ref<string | null>(null)
  const refreshToken = ref<string | null>(null)
  const expiresIn = ref<number>(0)
  const anonymousSessionId = ref<string | null>(null)
  const identityRevision = ref(0)
  let initializePromise: Promise<void> | null = null

  /* ===== Getters ===== */
  const isLoggedIn = computed(() => !!accessToken.value)
  const isAnonymous = computed(() => !!anonymousSessionId.value && !accessToken.value)

  /* ===== Actions ===== */

  /** 尝试恢复登录态 */
  function restoreSession() {
    const token = localStorage.getItem('access_token')
    const refresh = localStorage.getItem('refresh_token')
    const expires = localStorage.getItem('expires_in')
    const expiresAt = localStorage.getItem('expires_at')

    // 检查 token 是否已过期（优先用 expires_at 绝对时间戳）
    const anonId = localStorage.getItem('anonymous_session_id')
    if (anonId) {
      anonymousSessionId.value = anonId
    }

    if (token && expiresAt) {
      const isExpired = Date.now() > parseInt(expiresAt, 10)
      if (isExpired) {
        clearSession()
        return
      }
    }

    if (token) {
      accessToken.value = token
      refreshToken.value = refresh
      expiresIn.value = expires ? parseInt(expires) : 7200
    }

    if (!token) {
      createAnonymousSession()
    }
  }

  function initializeSession(): Promise<void> {
    if (initializePromise) return initializePromise
    initializePromise = (async () => {
      restoreSession()
      if (accessToken.value && anonymousSessionId.value) {
        try {
          await mergeAnonymousData()
        } catch {
          // 保留匿名 ID，后续启动时重试
        }
      }
    })()
    return initializePromise
  }

  /** 发送短信验证码 */
  async function sendSmsCode(phone: string) {
    const res = await apiSendSms({ phone })
    return res.data.data
  }

  /** 手机号登录 */
  async function login(phone: string, code: string) {
    const res = await apiLogin({ method: 'phone', phone, code })
    const { access_token, refresh_token: refresh, expires_in, user: userData } = res.data.data!

    accessToken.value = access_token
    refreshToken.value = refresh
    expiresIn.value = expires_in
    user.value = userData

    // 计算并存储绝对过期时间戳
    const expiresAt = Date.now() + expires_in * 1000

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh)
    localStorage.setItem('expires_in', String(expires_in))
    localStorage.setItem('expires_at', String(expiresAt))

    // 登录后自动合并匿名数据
    if (anonymousSessionId.value) {
      try {
        await mergeAnonymousData()
      } catch {
        // 合并失败不影响登录
      }
    }
    initializePromise = null
    identityRevision.value++
  }

  /** 密码登录 */
  async function loginWithPassword(phone: string, password: string) {
    const res = await apiLogin({ method: 'password', phone, password })
    const { access_token, refresh_token: refresh, expires_in, user: userData } = res.data.data!

    accessToken.value = access_token
    refreshToken.value = refresh
    expiresIn.value = expires_in
    user.value = userData

    const expiresAt = Date.now() + expires_in * 1000

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh)
    localStorage.setItem('expires_in', String(expires_in))
    localStorage.setItem('expires_at', String(expiresAt))

    // 登录后自动合并匿名数据
    if (anonymousSessionId.value) {
      try {
        await mergeAnonymousData()
      } catch {
        // 合并失败不影响登录
      }
    }
    initializePromise = null
    identityRevision.value++
  }

  /** 注册（手机号+密码），成功后自动登录 */
  async function register(phone: string, password: string, nickname?: string) {
    const res = await apiRegister({ phone, password, nickname })
    const { access_token, refresh_token: refresh, expires_in, user: userData } = res.data.data!

    accessToken.value = access_token
    refreshToken.value = refresh
    expiresIn.value = expires_in
    user.value = userData

    const expiresAt = Date.now() + expires_in * 1000

    localStorage.setItem('access_token', access_token)
    localStorage.setItem('refresh_token', refresh)
    localStorage.setItem('expires_in', String(expires_in))
    localStorage.setItem('expires_at', String(expiresAt))

    // 注册成功后合并匿名数据
    if (anonymousSessionId.value) {
      try {
        await mergeAnonymousData()
      } catch {
        // 合并失败不影响注册
      }
    }
    initializePromise = null
    identityRevision.value++
  }

  /** 登出 */
  async function logout() {
    try {
      await apiLogout()
    } catch {
      // 服务端登出失败仍清除本地
    }
    clearSession()
  }

  /** 创建匿名会话 */
  function createAnonymousSession(): string {
    const existing = anonymousSessionId.value || localStorage.getItem('anonymous_session_id')
    if (existing) {
      anonymousSessionId.value = existing
      return existing
    }
    const id = `sess_anonymous_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`
    anonymousSessionId.value = id
    localStorage.setItem('anonymous_session_id', id)
    return id
  }

  /** 合并匿名数据 */
  async function mergeAnonymousData() {
    if (!anonymousSessionId.value) return
    const res = await apiMerge({ anonymous_session_id: anonymousSessionId.value })
    anonymousSessionId.value = null
    localStorage.removeItem('anonymous_session_id')
    return res.data.data
  }

  /** 清除登录态 */
  function clearSession() {
    accessToken.value = null
    refreshToken.value = null
    expiresIn.value = 0
    user.value = null
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    localStorage.removeItem('expires_in')
    localStorage.removeItem('expires_at')
    createAnonymousSession()
    initializePromise = null
    identityRevision.value++
  }

  return {
    user,
    accessToken,
    refreshToken,
    expiresIn,
    anonymousSessionId,
    identityRevision,
    isLoggedIn,
    isAnonymous,
    restoreSession,
    initializeSession,
    sendSmsCode,
    login,
    loginWithPassword,
    register,
    logout,
    createAnonymousSession,
    mergeAnonymousData,
    clearSession,
  }
})
